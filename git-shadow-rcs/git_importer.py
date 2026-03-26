#!/usr/bin/env python3
"""
Git Fast-Import Generator
Creates git fast-import format from RCS revisions
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, TextIO
from datetime import datetime
from rcs_parser import RCSFile, RCSRevision, RCSParser
from author_map import AuthorMapper, create_author_mapper


class GitImporter:
    """Generate git fast-import commands from RCS history"""

    def __init__(
        self,
        git_repo: Path,
        rcs_root: Path,
        author_mapper: Optional[AuthorMapper] = None,
    ):
        """
        Initialize Git importer

        Args:
            git_repo: Path to git repository
            rcs_root: Path to RCS root directory
            author_mapper: Optional AuthorMapper instance for username mapping
        """
        self.git_repo = Path(git_repo)
        self.rcs_root = Path(rcs_root)
        self.author_mapper = author_mapper or AuthorMapper()
        self.parser = RCSParser(rcs_root)

        # Ensure git repo exists
        if not (self.git_repo / ".git").exists():
            raise ValueError(f"Git repository not found at {git_repo}")

    def map_author(self, username: str) -> str:
        """
        Map RCS username to git author format

        Args:
            username: RCS username

        Returns:
            Git author string in format "Name <email>"
        """
        return self.author_mapper.map_author(username)

    def get_relative_path(self, working_file: Path) -> Path:
        """
        Get path relative to RCS root

        Args:
            working_file: Absolute or relative path to working file

        Returns:
            Path relative to RCS root
        """
        try:
            return working_file.relative_to(self.rcs_root)
        except ValueError:
            # If not relative to rcs_root, return as-is
            return working_file

    def generate_fast_import_commands(
        self,
        rcs_files: List[RCSFile],
        output: TextIO,
        branch: str = "master",
        commit_fuzz: int = 300,  # 5 minutes in seconds
    ):
        """
        Generate git fast-import commands for RCS files

        Args:
            rcs_files: List of RCSFile objects with revision history
            output: File object to write fast-import commands to
            branch: Git branch name to import into
            commit_fuzz: Time window (seconds) for coalescing commits
        """
        # Collect all revisions with file information
        all_commits = []

        for rcs_file in rcs_files:
            rel_path = self.get_relative_path(rcs_file.working_file)

            for revision in rcs_file.revisions:
                all_commits.append(
                    {
                        "rcs_file": rcs_file,
                        "revision": revision,
                        "rel_path": rel_path,
                        "date": revision.date,
                        "author": revision.author,
                        "log": revision.log,
                    }
                )

        # Sort by date
        all_commits.sort(key=lambda x: x["date"])

        # Coalesce commits within fuzz window
        coalesced = self._coalesce_commits(all_commits, commit_fuzz)

        # Generate fast-import commands
        mark_counter = 1
        blob_marks = {}  # Cache for blob marks

        for commit_group in coalesced:
            # Get commit metadata from first commit in group
            first = commit_group[0]
            date = first["date"]
            author = self.map_author(first["author"])
            log = first["log"]

            # Use timestamp as timezone-aware format
            timestamp = int(date.timestamp())
            tz = date.strftime("%z") or "+0000"
            date_str = f"{timestamp} {tz}"

            # Write commit header
            output.write(f"commit refs/heads/{branch}\n")
            output.write(f"mark :{mark_counter}\n")
            mark_counter += 1
            output.write(f"author {author} {date_str}\n")
            output.write(f"committer {author} {date_str}\n")

            # Write log message
            log_bytes = log.encode("utf-8")
            output.write(f"data {len(log_bytes)}\n")
            output.write(log + "\n")

            # Write file modifications for all files in this commit
            for commit_info in commit_group:
                rcs_file = commit_info["rcs_file"]
                revision = commit_info["revision"]
                rel_path = commit_info["rel_path"]

                # Check if file is deleted
                if revision.state.lower() == "dead":
                    output.write(f"D {rel_path}\n")
                else:
                    # Generate blob mark for this file revision
                    blob_key = (str(rcs_file.rcs_file), revision.revision)

                    if blob_key not in blob_marks:
                        blob_marks[blob_key] = mark_counter
                        mark_counter += 1

                        # Extract file content
                        content = self.parser.extract_revision_content(
                            rcs_file.rcs_file, revision.revision
                        )

                        if content is not None:
                            # Write blob
                            output.write(f"blob\n")
                            output.write(f"mark :{blob_marks[blob_key]}\n")
                            output.write(f"data {len(content)}\n")
                            output.write(content.decode("utf-8", errors="replace"))
                            output.write("\n")

                    # Reference the blob in the commit
                    blob_mark = blob_marks[blob_key]
                    # Use 100644 for regular files
                    output.write(f"M 100644 :{blob_mark} {rel_path}\n")

            output.write("\n")

    def _coalesce_commits(self, commits: List[Dict], fuzz: int) -> List[List[Dict]]:
        """
        Coalesce commits that occur within a time window and have same author/log

        Args:
            commits: Sorted list of commit dictionaries
            fuzz: Time window in seconds

        Returns:
            List of commit groups (each group will become one git commit)
        """
        if not commits:
            return []

        coalesced = []
        current_group = [commits[0]]

        for commit in commits[1:]:
            last = current_group[0]

            # Check if this commit should be coalesced with current group
            time_diff = abs((commit["date"] - last["date"]).total_seconds())
            same_author = commit["author"] == last["author"]
            same_log = commit["log"] == last["log"]

            # Check if file is already in current group
            current_files = {c["rel_path"] for c in current_group}
            same_file = commit["rel_path"] in current_files

            if time_diff <= fuzz and same_author and same_log and not same_file:
                # Coalesce with current group
                current_group.append(commit)
            else:
                # Start new group
                coalesced.append(current_group)
                current_group = [commit]

        # Add last group
        coalesced.append(current_group)

        return coalesced

    def import_to_git(
        self, rcs_files: List[RCSFile], branch: str = "master", commit_fuzz: int = 300
    ) -> bool:
        """
        Import RCS files directly into git repository

        Args:
            rcs_files: List of RCSFile objects
            branch: Branch to import into
            commit_fuzz: Time window for coalescing commits

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create a temporary file for fast-import commands
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".fi") as f:
                temp_file = f.name
                # Type: ignore for NamedTemporaryFile compatibility with TextIO
                self.generate_fast_import_commands(rcs_files, f, branch, commit_fuzz)  # type: ignore[arg-type]

            # Run git fast-import
            with open(temp_file, "r") as f:
                result = subprocess.run(
                    ["git", "fast-import", "--quiet"],
                    stdin=f,
                    cwd=self.git_repo,
                    capture_output=True,
                    text=True,
                )

            # Clean up temp file
            os.unlink(temp_file)

            if result.returncode != 0:
                print(f"Error: git fast-import failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            print(f"Error during import: {e}")
            return False

    def import_revisions_since(
        self, since_date: datetime, branch: str = "master", commit_fuzz: int = 300
    ) -> bool:
        """
        Import only revisions that occurred after a specific date

        Args:
            since_date: Only import revisions after this date
            branch: Branch to import into
            commit_fuzz: Time window for coalescing commits

        Returns:
            True if successful, False otherwise
        """
        # Get all RCS files
        all_rcs_files = self.parser.get_all_files_with_history()

        # Filter revisions to only those after since_date
        filtered_files = []
        for rcs_file in all_rcs_files:
            new_revisions = [r for r in rcs_file.revisions if r.date > since_date]
            if new_revisions:
                # Create new RCSFile with filtered revisions
                filtered_file = RCSFile(
                    working_file=rcs_file.working_file,
                    rcs_file=rcs_file.rcs_file,
                    head=rcs_file.head,
                    branch=rcs_file.branch,
                    revisions=new_revisions,
                )
                filtered_files.append(filtered_file)

        if not filtered_files:
            print(f"No revisions found after {since_date}")
            return True

        print(
            f"Importing {sum(len(f.revisions) for f in filtered_files)} revisions from {len(filtered_files)} files"
        )

        return self.import_to_git(filtered_files, branch, commit_fuzz)


if __name__ == "__main__":
    # Test the importer
    import sys

    if len(sys.argv) < 3:
        print("Usage: python git_importer.py <rcs_directory> <git_repo> [authors_file]")
        sys.exit(1)

    rcs_root = Path(sys.argv[1])
    git_repo = Path(sys.argv[2])

    # Load author mappings if file provided
    author_file = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    author_mapper = create_author_mapper(author_file)

    if author_file:
        print(f"Loaded {len(author_mapper.get_all_mappings())} author mappings")

    importer = GitImporter(git_repo, rcs_root, author_mapper)

    print("Parsing all RCS files...")
    parser = RCSParser(rcs_root)
    rcs_files = parser.get_all_files_with_history()

    print(f"Found {len(rcs_files)} RCS files with history")
    print(f"Total revisions: {sum(len(f.revisions) for f in rcs_files)}")

    print("\nGenerating fast-import commands...")
    import sys

    importer.generate_fast_import_commands(rcs_files, sys.stdout)
