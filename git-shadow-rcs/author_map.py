#!/usr/bin/env python3
"""
Author Mapping Module
Handles mapping of RCS usernames to Git author format
"""

from pathlib import Path
from typing import Dict, Optional


class AuthorMapper:
    """Map RCS usernames to Git author format"""

    def __init__(self, author_map: Optional[Dict[str, str]] = None):
        """
        Initialize author mapper

        Args:
            author_map: Optional dictionary mapping RCS usernames to Git authors
                       e.g., {'john': 'John Doe <john@example.com>'}
        """
        self.author_map = author_map or {}

    def map_author(self, username: str) -> str:
        """
        Map RCS username to git author format

        Args:
            username: RCS username

        Returns:
            Git author string in format "Name <email>"
        """
        if username in self.author_map:
            return self.author_map[username]
        else:
            # Default format if not in map
            return f"{username} <{username}@localhost>"

    def add_mapping(self, username: str, author: str):
        """
        Add a new author mapping

        Args:
            username: RCS username
            author: Git author format "Name <email>"
        """
        self.author_map[username] = author

    def get_all_mappings(self) -> Dict[str, str]:
        """
        Get all author mappings

        Returns:
            Dictionary of all username to author mappings
        """
        return self.author_map.copy()


def load_author_map_file(author_file: Optional[Path]) -> Dict[str, str]:
    """
    Load author map from file

    File format (one per line):
        username = Full Name <email@example.com>
        # Comments are ignored

    Example:
        jdoe = John Doe <jdoe@example.com>
        admin = System Admin <admin@example.com>

    Args:
        author_file: Path to author map file

    Returns:
        Dictionary mapping usernames to author strings
    """
    if not author_file or not author_file.exists():
        return {}

    author_map = {}
    with open(author_file, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse username = Author Name <email>
            if "=" in line:
                username, author = line.split("=", 1)
                username = username.strip()
                author = author.strip()

                # Validate format
                if not username:
                    print(
                        f"Warning: Empty username on line {line_num} in {author_file}"
                    )
                    continue

                if not author:
                    print(f"Warning: Empty author on line {line_num} in {author_file}")
                    continue

                # Basic email format validation
                if "<" in author and ">" in author:
                    if "@" not in author:
                        print(
                            f"Warning: Invalid email format on line {line_num} in {author_file}"
                        )

                author_map[username] = author
            else:
                print(
                    f"Warning: Invalid format on line {line_num} in {author_file} (expected 'username = author')"
                )

    return author_map


def save_author_map_file(author_map: Dict[str, str], author_file: Path):
    """
    Save author map to file

    Args:
        author_map: Dictionary of username to author mappings
        author_file: Path to save the author map file
    """
    with open(author_file, "w") as f:
        f.write("# RCS to Git Author Mapping\n")
        f.write("#\n")
        f.write("# Format: rcs_username = Full Name <email@example.com>\n")
        f.write("#\n\n")

        for username in sorted(author_map.keys()):
            f.write(f"{username} = {author_map[username]}\n")


def create_author_mapper(author_file: Optional[Path] = None) -> AuthorMapper:
    """
    Create an AuthorMapper instance from a file

    Args:
        author_file: Optional path to author mapping file

    Returns:
        AuthorMapper instance with loaded mappings
    """
    author_map = load_author_map_file(author_file) if author_file else {}
    return AuthorMapper(author_map)


if __name__ == "__main__":
    # Test the author mapper
    import sys

    if len(sys.argv) < 2:
        print("Usage: python author_map.py <authors_file>")
        sys.exit(1)

    author_file = Path(sys.argv[1])
    mapper = create_author_mapper(author_file)

    print(f"Loaded {len(mapper.get_all_mappings())} author mappings:")
    for username, author in sorted(mapper.get_all_mappings().items()):
        print(f"  {username:15} -> {author}")

    # Test mapping
    print("\nTesting mappings:")
    test_users = ["admin", "root", "unknown_user"]
    for user in test_users:
        print(f"  {user:15} -> {mapper.map_author(user)}")
