#!/usr/bin/env python3
"""
Generate Authors File from RCS Logs

Scans RCS directory and extracts unique author usernames from commit logs.
Creates an initial authors.txt file template that can be edited with proper
name and email information.
"""

import argparse
import sys
from pathlib import Path
from typing import Set, Dict
from collections import defaultdict

from rcs_parser import RCSParser
from author_map import save_author_map_file


def extract_authors_from_rcs(rcs_root: Path, verbose: bool = False) -> Dict[str, int]:
    """
    Extract all unique authors from RCS files

    Args:
        rcs_root: Root directory containing RCS files
        verbose: Print progress information

    Returns:
        Dictionary mapping author usernames to commit count
    """
    parser = RCSParser(rcs_root)

    if verbose:
        print(f"Scanning RCS directory: {rcs_root}")

    # Find all RCS files
    rcs_files = parser.find_rcs_files()

    if not rcs_files:
        print(f"Warning: No RCS files found in {rcs_root}", file=sys.stderr)
        return {}

    if verbose:
        print(f"Found {len(rcs_files)} RCS files")

    # Track authors and their commit counts
    author_commits = defaultdict(int)

    # Parse each RCS file and extract authors
    for i, rcs_file in enumerate(rcs_files, 1):
        if verbose and i % 10 == 0:
            print(f"  Processed {i}/{len(rcs_files)} files...")

        try:
            rcs_info = parser.parse_rlog(rcs_file)
            if rcs_info:
                for revision in rcs_info.revisions:
                    if revision.author:
                        author_commits[revision.author] += 1
        except Exception as e:
            if verbose:
                print(f"Warning: Failed to parse {rcs_file}: {e}", file=sys.stderr)
            continue

    if verbose:
        print(f"  Processed {len(rcs_files)}/{len(rcs_files)} files")
        print(f"\nFound {len(author_commits)} unique authors")

    return dict(author_commits)


def generate_author_map(
    authors: Dict[str, int], use_local_domain: bool = True
) -> Dict[str, str]:
    """
    Generate initial author map with template entries

    Args:
        authors: Dictionary of author usernames to commit counts
        use_local_domain: Use @localhost for email domain

    Returns:
        Dictionary mapping usernames to Git author format
    """
    author_map = {}

    for username in authors:
        # Create a reasonable default name from username
        # Convert underscore/dot to space and capitalize
        display_name = username.replace("_", " ").replace(".", " ").title()

        # Generate email
        if use_local_domain:
            email = f"{username}@localhost"
        else:
            email = f"{username}@example.com"

        # Git author format
        author_map[username] = f"{display_name} <{email}>"

    return author_map


def main():
    parser = argparse.ArgumentParser(
        description="Generate authors.txt file from RCS commit logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate authors file from RCS directory:
  %(prog)s --rcs-root /path/to/rcs --output authors.txt

  # Show what authors would be generated without writing file:
  %(prog)s --rcs-root /path/to/rcs --dry-run

  # Show statistics about commits per author:
  %(prog)s --rcs-root /path/to/rcs --stats

  # Use example.com domain instead of localhost:
  %(prog)s --rcs-root /path/to/rcs --domain example.com
""",
    )

    parser.add_argument(
        "--rcs-root",
        type=Path,
        required=True,
        help="Path to RCS root directory",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("authors.txt"),
        help="Output file path (default: authors.txt)",
    )

    parser.add_argument(
        "--domain",
        default="localhost",
        help="Email domain to use (default: localhost)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing file",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show commit statistics per author",
    )

    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing authors file instead of overwriting",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Validate RCS root
    if not args.rcs_root.exists():
        print(f"Error: RCS root directory not found: {args.rcs_root}", file=sys.stderr)
        return 1

    # Extract authors from RCS logs
    author_commits = extract_authors_from_rcs(args.rcs_root, args.verbose)

    if not author_commits:
        print("No authors found in RCS logs", file=sys.stderr)
        return 1

    # Show statistics if requested
    if args.stats:
        print("\nCommit statistics per author:")
        print("-" * 50)
        # Sort by commit count (descending)
        sorted_authors = sorted(
            author_commits.items(), key=lambda x: x[1], reverse=True
        )
        for username, count in sorted_authors:
            print(f"  {username:20} {count:6} commits")
        print("-" * 50)
        print(
            f"  Total: {sum(author_commits.values())} commits by {len(author_commits)} authors"
        )
        print()

    # Generate author map
    use_local = args.domain == "localhost"
    author_map = generate_author_map(author_commits, use_local)

    # If not using localhost, update email domain
    if not use_local:
        for username in author_map:
            # Replace @localhost or @example.com with specified domain
            author_map[username] = author_map[username].replace(
                "@localhost", f"@{args.domain}"
            )
            author_map[username] = author_map[username].replace(
                "@example.com", f"@{args.domain}"
            )

    # Handle append mode
    if args.append and args.output.exists():
        from author_map import load_author_map_file

        existing_map = load_author_map_file(args.output)

        # Only add new authors
        new_authors = 0
        for username, author in author_map.items():
            if username not in existing_map:
                existing_map[username] = author
                new_authors += 1

        author_map = existing_map

        if args.verbose:
            print(f"Appending {new_authors} new authors to existing file")

    # Display generated mappings
    print(f"\nGenerated {len(author_map)} author mappings:")
    print("=" * 70)
    for username in sorted(author_map.keys()):
        commits = author_commits.get(username, 0)
        print(f"  {username:20} -> {author_map[username]:35} ({commits} commits)")
    print("=" * 70)

    # Write to file or dry-run
    if args.dry_run:
        print(f"\nDry run - no file written")
        print(f"Would write to: {args.output}")
    else:
        # Create backup if file exists and not appending
        if args.output.exists() and not args.append:
            backup_path = args.output.with_suffix(args.output.suffix + ".bak")
            import shutil

            shutil.copy2(args.output, backup_path)
            print(f"\nBackup created: {backup_path}")

        # Save to file
        save_author_map_file(author_map, args.output)
        print(f"\n✓ Author mappings written to: {args.output}")
        print(f"\nNext steps:")
        print(f"  1. Edit {args.output} to add real names and email addresses")
        print(f"  2. Use with: rcs_monitor.py --authors {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
