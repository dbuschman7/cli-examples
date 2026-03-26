#!/usr/bin/env python3
"""
RCS Parser Module
Extracts revision history from RCS files and directories
"""

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class RCSRevision:
    """Represents a single RCS revision"""

    revision: str
    date: datetime
    author: str
    state: str
    log: str
    branches: List[str] = field(default_factory=list)

    def __str__(self):
        return f"Rev {self.revision} by {self.author} on {self.date}"


@dataclass
class RCSFile:
    """Represents an RCS file with its history"""

    working_file: Path
    rcs_file: Path
    head: str
    branch: Optional[str]
    access: List[str] = field(default_factory=list)
    symbols: Dict[str, str] = field(default_factory=dict)
    locks: Dict[str, str] = field(default_factory=dict)
    revisions: List[RCSRevision] = field(default_factory=list)

    def __str__(self):
        return (
            f"{self.working_file} (head: {self.head}, {len(self.revisions)} revisions)"
        )


class RCSParser:
    """Parse RCS files and extract revision information"""

    def __init__(self, rcs_root: Path):
        """
        Initialize RCS parser

        Args:
            rcs_root: Root directory containing RCS files (could have RCS/ subdirs)
        """
        self.rcs_root = Path(rcs_root)
        if not self.rcs_root.exists():
            raise ValueError(f"RCS root directory does not exist: {rcs_root}")

    def find_rcs_files(self) -> List[Path]:
        """
        Find all RCS files in the directory tree

        Returns:
            List of paths to ,v files
        """
        rcs_files = []

        # Look for ,v files directly in tree
        for file in self.rcs_root.rglob("*,v"):
            rcs_files.append(file)

        # Look for files in RCS/ subdirectories
        for rcs_dir in self.rcs_root.rglob("RCS"):
            if rcs_dir.is_dir():
                for file in rcs_dir.glob("*,v"):
                    rcs_files.append(file)

        return sorted(rcs_files)

    def get_working_file_path(self, rcs_file: Path) -> Path:
        """
        Determine the working file path from an RCS file path

        Args:
            rcs_file: Path to the ,v RCS file

        Returns:
            Path to the working file
        """
        # Remove ,v suffix
        basename = rcs_file.name[:-2]  # Remove ,v

        # If file is in RCS/ subdirectory, working file is in parent
        if rcs_file.parent.name == "RCS":
            return rcs_file.parent.parent / basename
        else:
            # Otherwise, working file is in same directory
            return rcs_file.parent / basename

    def parse_rlog(self, rcs_file: Path) -> Optional[RCSFile]:
        """
        Parse RCS file using rlog command

        Args:
            rcs_file: Path to the ,v file

        Returns:
            RCSFile object with parsed information
        """
        try:
            # Run rlog to get revision information
            result = subprocess.run(
                ["rlog", str(rcs_file)], capture_output=True, text=True, check=True
            )

            return self._parse_rlog_output(rcs_file, result.stdout)

        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to parse {rcs_file}: {e}")
            return None
        except FileNotFoundError:
            print("Error: 'rlog' command not found. Please install RCS.")
            raise

    def _parse_rlog_output(self, rcs_file: Path, output: str) -> RCSFile:
        """
        Parse the output from rlog command

        Args:
            rcs_file: Path to RCS file
            output: stdout from rlog command

        Returns:
            Parsed RCSFile object
        """
        lines = output.split("\n")

        # Initialize RCSFile
        working_file = self.get_working_file_path(rcs_file)
        rcs_info = RCSFile(
            working_file=working_file, rcs_file=rcs_file, head="", branch=None
        )

        # Parse header section
        in_description = False
        in_revision = False
        current_revision = None
        log_lines = []

        for line in lines:
            # Header fields
            if line.startswith("RCS file:"):
                pass
            elif line.startswith("Working file:"):
                pass
            elif line.startswith("head:"):
                rcs_info.head = line.split(":", 1)[1].strip()
            elif line.startswith("branch:"):
                branch = line.split(":", 1)[1].strip()
                rcs_info.branch = branch if branch else None
            elif line.startswith("locks:"):
                pass  # Could parse locks if needed
            elif line.startswith("access list:"):
                pass  # Could parse access list if needed
            elif line.startswith("symbolic names:"):
                # Next lines contain symbolic names
                pass
            elif line.startswith("\t") and ":" in line and not in_revision:
                # Symbolic name mapping
                parts = line.strip().split(":", 1)
                if len(parts) == 2:
                    rcs_info.symbols[parts[0].strip()] = parts[1].strip()
            elif line.startswith("description:"):
                in_description = True
            elif line.startswith("----------------------------"):
                # Start of revision entry
                in_description = False
                in_revision = False
                if current_revision and log_lines:
                    current_revision.log = "\n".join(log_lines).strip()
                    rcs_info.revisions.append(current_revision)
                    log_lines = []
            elif line.startswith("revision "):
                in_revision = True
                rev_num = line.split()[1]
                current_revision = RCSRevision(
                    revision=rev_num,
                    date=datetime.now(),  # Will be updated
                    author="",
                    state="",
                    log="",
                )
            elif in_revision and line.startswith("date:"):
                # Parse date, author, state, branches
                # Format: date: 2025/12/19 14:30:00;  author: user;  state: Exp;  lines: +1 -0
                if not current_revision:
                    continue

                parts = line.split(";")

                for part in parts:
                    part = part.strip()
                    if part.startswith("date:"):
                        date_str = part.split(":", 1)[1].strip()
                        try:
                            current_revision.date = datetime.strptime(
                                date_str, "%Y/%m/%d %H:%M:%S"
                            )
                        except ValueError:
                            # Try alternative format
                            try:
                                current_revision.date = datetime.strptime(
                                    date_str, "%Y-%m-%d %H:%M:%S"
                                )
                            except ValueError:
                                print(f"Warning: Could not parse date: {date_str}")
                    elif part.startswith("author:"):
                        current_revision.author = part.split(":", 1)[1].strip()
                    elif part.startswith("state:"):
                        current_revision.state = part.split(":", 1)[1].strip()
                    elif part.startswith("branches:"):
                        branches_str = part.split(":", 1)[1].strip()
                        current_revision.branches = branches_str.split()
            elif (
                in_revision
                and not line.startswith("date:")
                and not line.startswith("---")
            ):
                # Log message lines
                log_lines.append(line)

        # Add last revision
        if current_revision and log_lines:
            current_revision.log = "\n".join(log_lines).strip()
            rcs_info.revisions.append(current_revision)

        return rcs_info

    def extract_revision_content(
        self, rcs_file: Path, revision: str
    ) -> Optional[bytes]:
        """
        Extract the content of a specific revision

        Args:
            rcs_file: Path to RCS file
            revision: Revision number (e.g., '1.1')

        Returns:
            Content as bytes, or None if extraction fails
        """
        try:
            result = subprocess.run(
                ["co", "-q", f"-p{revision}", str(rcs_file)],
                capture_output=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(
                f"Warning: Failed to extract revision {revision} from {rcs_file}: {e}"
            )
            return None

    def get_latest_revision(self, rcs_file: Path) -> Optional[RCSRevision]:
        """
        Get the latest (head) revision for an RCS file

        Args:
            rcs_file: Path to RCS file

        Returns:
            Latest RCSRevision or None
        """
        rcs_info = self.parse_rlog(rcs_file)
        if rcs_info and rcs_info.revisions:
            # Revisions are in reverse chronological order from rlog
            return rcs_info.revisions[0]
        return None

    def get_all_files_with_history(self) -> List[RCSFile]:
        """
        Get all RCS files with their complete revision history

        Returns:
            List of RCSFile objects
        """
        rcs_files = self.find_rcs_files()
        results = []

        for rcs_file in rcs_files:
            rcs_info = self.parse_rlog(rcs_file)
            if rcs_info:
                results.append(rcs_info)

        return results

    def get_revisions_since(
        self, rcs_file: Path, since_date: datetime
    ) -> List[RCSRevision]:
        """
        Get revisions that occurred after a specific date

        Args:
            rcs_file: Path to RCS file
            since_date: Only return revisions after this date

        Returns:
            List of RCSRevision objects
        """
        rcs_info = self.parse_rlog(rcs_file)
        if not rcs_info:
            return []

        return [rev for rev in rcs_info.revisions if rev.date > since_date]


if __name__ == "__main__":
    # Test the parser
    import sys

    if len(sys.argv) < 2:
        print("Usage: python rcs_parser.py <rcs_directory>")
        sys.exit(1)

    parser = RCSParser(Path(sys.argv[1]))

    print("Finding RCS files...")
    rcs_files = parser.find_rcs_files()
    print(f"Found {len(rcs_files)} RCS files")

    print("\nParsing RCS files...")
    for rcs_file in rcs_files[:5]:  # Show first 5
        print(f"\n{rcs_file}")
        rcs_info = parser.parse_rlog(rcs_file)
        if rcs_info:
            print(f"  {rcs_info}")
            for rev in rcs_info.revisions[:3]:  # Show first 3 revisions
                print(f"    {rev}")
