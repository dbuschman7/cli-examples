#!/usr/bin/env python3
"""
RCS to Git Monitor
Monitors RCS directory and imports new commits to Git repository

This script can be run as a cron job to periodically sync RCS commits to Git.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

from rcs_parser import RCSParser
from git_importer import GitImporter
from author_map import AuthorMapper, load_author_map_file, create_author_mapper


class RCSMonitor:
    """Monitor RCS directory and sync to Git"""

    def __init__(
        self,
        rcs_root: Path,
        git_repo: Path,
        state_file: Optional[Path] = None,
        author_mapper: Optional[AuthorMapper] = None,
    ):
        """
        Initialize RCS monitor

        Args:
            rcs_root: Path to RCS root directory
            git_repo: Path to Git repository
            state_file: Path to state file tracking last sync
            author_mapper: Optional AuthorMapper instance for username mapping
        """
        self.rcs_root = Path(rcs_root)
        self.git_repo = Path(git_repo)
        self.state_file = state_file or (self.git_repo / ".rcs_sync_state.json")
        self.author_mapper = author_mapper or AuthorMapper()

        self.parser = RCSParser(rcs_root)
        self.importer = GitImporter(git_repo, rcs_root, author_mapper)

    def load_state(self) -> Dict:
        """
        Load sync state from file

        Returns:
            State dictionary with last_sync timestamp
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    # Convert timestamp back to datetime
                    if "last_sync" in state:
                        state["last_sync"] = datetime.fromisoformat(state["last_sync"])
                    return state
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Warning: Could not load state file: {e}")
                return {}
        return {}

    def save_state(self, state: Dict):
        """
        Save sync state to file

        Args:
            state: State dictionary to save
        """
        # Convert datetime to ISO format for JSON
        state_copy = state.copy()
        if "last_sync" in state_copy and isinstance(state_copy["last_sync"], datetime):
            state_copy["last_sync"] = state_copy["last_sync"].isoformat()

        with open(self.state_file, "w") as f:
            json.dump(state_copy, f, indent=2)

    def get_last_sync_time(self) -> Optional[datetime]:
        """
        Get the last sync timestamp

        Returns:
            Datetime of last sync, or None if never synced
        """
        state = self.load_state()
        return state.get("last_sync")

    def sync_new_commits(
        self, branch: str = "master", commit_fuzz: int = 300, dry_run: bool = False
    ) -> bool:
        """
        Sync new RCS commits to Git

        Args:
            branch: Git branch to import into
            commit_fuzz: Time window for coalescing commits (seconds)
            dry_run: If True, show what would be done without actually importing

        Returns:
            True if successful, False otherwise
        """
        # Get last sync time
        last_sync = self.get_last_sync_time()

        if last_sync:
            print(f"Last sync: {last_sync}")
            since_date = last_sync
        else:
            print("No previous sync found - will only sync recent commits")
            # If no previous sync, only import commits from last 7 days
            # to avoid importing entire history on first run
            since_date = datetime.now() - timedelta(days=7)
            print(f"Syncing commits since: {since_date}")

        # Get all RCS files with their revisions
        print("Scanning RCS files...")
        all_rcs_files = self.parser.get_all_files_with_history()
        print(f"Found {len(all_rcs_files)} RCS files")

        # Filter to only new revisions
        new_revisions_count = 0
        filtered_files = []

        for rcs_file in all_rcs_files:
            new_revisions = [r for r in rcs_file.revisions if r.date > since_date]
            if new_revisions:
                from rcs_parser import RCSFile

                filtered_file = RCSFile(
                    working_file=rcs_file.working_file,
                    rcs_file=rcs_file.rcs_file,
                    head=rcs_file.head,
                    branch=rcs_file.branch,
                    revisions=new_revisions,
                )
                filtered_files.append(filtered_file)
                new_revisions_count += len(new_revisions)

        if not filtered_files:
            print("No new revisions to sync")
            return True

        print(
            f"\nFound {new_revisions_count} new revisions in {len(filtered_files)} files:"
        )
        for rcs_file in filtered_files:
            print(
                f"  {rcs_file.working_file.name}: {len(rcs_file.revisions)} revisions"
            )

        if dry_run:
            print("\nDry run - no changes made")
            return True

        # Import to Git
        print(f"\nImporting to Git branch '{branch}'...")
        success = self.importer.import_to_git(filtered_files, branch, commit_fuzz)

        if success:
            # Update state file with current time
            current_time = datetime.now()
            state = {
                "last_sync": current_time,
                "revisions_synced": new_revisions_count,
                "files_synced": len(filtered_files),
            }
            self.save_state(state)
            print(f"\n✓ Successfully synced {new_revisions_count} revisions")
            print(f"  State saved to {self.state_file}")
        else:
            print("\n✗ Sync failed")

        return success

    def force_sync_all(
        self, branch: str = "master", commit_fuzz: int = 300, dry_run: bool = False
    ) -> bool:
        """
        Force sync of all RCS history (ignoring state file)

        Args:
            branch: Git branch to import into
            commit_fuzz: Time window for coalescing commits (seconds)
            dry_run: If True, show what would be done without actually importing

        Returns:
            True if successful, False otherwise
        """
        print("Force syncing all RCS history...")

        # Get all RCS files
        all_rcs_files = self.parser.get_all_files_with_history()
        total_revisions = sum(len(f.revisions) for f in all_rcs_files)

        print(
            f"Found {len(all_rcs_files)} RCS files with {total_revisions} total revisions"
        )

        if dry_run:
            print("\nDry run - no changes made")
            return True

        # Import to Git
        print(f"\nImporting to Git branch '{branch}'...")
        success = self.importer.import_to_git(all_rcs_files, branch, commit_fuzz)

        if success:
            # Update state file
            current_time = datetime.now()
            state = {
                "last_sync": current_time,
                "revisions_synced": total_revisions,
                "files_synced": len(all_rcs_files),
                "force_sync": True,
            }
            self.save_state(state)
            print(f"\n✓ Successfully synced {total_revisions} revisions")
        else:
            print("\n✗ Sync failed")

        return success


def main():
    parser = argparse.ArgumentParser(
        description="Monitor RCS directory and sync commits to Git",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initial import of all history:
  %(prog)s --rcs-root /path/to/rcs --git-repo /path/to/git --initial

  # Sync new commits (for cron):
  %(prog)s --rcs-root /path/to/rcs --git-repo /path/to/git

  # Dry run to see what would be synced:
  %(prog)s --rcs-root /path/to/rcs --git-repo /path/to/git --dry-run

  # With custom author mapping:
  %(prog)s --rcs-root /path/to/rcs --git-repo /path/to/git --authors authors.txt
""",
    )

    parser.add_argument(
        "--rcs-root", type=Path, required=True, help="Path to RCS root directory"
    )

    parser.add_argument(
        "--git-repo", type=Path, required=True, help="Path to Git repository"
    )

    parser.add_argument(
        "--branch", default="master", help="Git branch to import into (default: master)"
    )

    parser.add_argument("--authors", type=Path, help="Path to author mapping file")

    parser.add_argument(
        "--commit-fuzz",
        type=int,
        default=300,
        help="Time window for coalescing commits in seconds (default: 300)",
    )

    parser.add_argument(
        "--initial",
        action="store_true",
        help="Perform initial import of all history (ignores state file)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    parser.add_argument(
        "--state-file",
        type=Path,
        help="Path to state file (default: GIT_REPO/.rcs_sync_state.json)",
    )

    args = parser.parse_args()

    # Validate paths
    if not args.rcs_root.exists():
        print(f"Error: RCS root directory not found: {args.rcs_root}", file=sys.stderr)
        return 1

    if not (args.git_repo / ".git").exists():
        print(f"Error: Git repository not found: {args.git_repo}", file=sys.stderr)
        print("Initialize a git repository first with: git init", file=sys.stderr)
        return 1

    # Load author mapper
    author_mapper = create_author_mapper(args.authors)
    if args.authors and args.authors.exists():
        print(f"Loaded {len(author_mapper.get_all_mappings())} author mappings")

    # Create monitor
    monitor = RCSMonitor(args.rcs_root, args.git_repo, args.state_file, author_mapper)

    # Perform sync
    if args.initial:
        success = monitor.force_sync_all(args.branch, args.commit_fuzz, args.dry_run)
    else:
        success = monitor.sync_new_commits(args.branch, args.commit_fuzz, args.dry_run)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
