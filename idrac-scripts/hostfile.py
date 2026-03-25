#!/usr/bin/env python3
"""
Hostfile Management Module

Manages lists of hosts from text files with support for:
- Reading hosts from files
- Removing hosts when operations succeed
- Adding hosts
- Checking host existence
- Batch operations
- Backup and restore

Host file format:
  - One hostname/IP per line
  - Lines starting with # are comments
  - Empty lines are ignored
  - Whitespace is trimmed
"""

import os
import shutil
from pathlib import Path
from typing import List, Set, Optional, Callable
from datetime import datetime


class HostFile:
    """
    Manage a list of hosts from a text file.

    Features:
    - Read/write host lists
    - Remove successful hosts
    - Validate hosts
    - Backup functionality
    - Atomic file operations
    """

    def __init__(self, filepath: str, auto_backup: bool = True):
        """
        Initialize hostfile manager.

        Args:
            filepath: Path to the host file
            auto_backup: Automatically backup file before modifications
        """
        self.filepath = Path(filepath)
        self.auto_backup = auto_backup
        self._hosts_cache = None

    def exists(self) -> bool:
        """Check if hostfile exists."""
        return self.filepath.exists()

    def create(self, hosts: Optional[List[str]] = None) -> bool:
        """
        Create a new hostfile.

        Args:
            hosts: Initial list of hosts to add

        Returns:
            True if created successfully
        """
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(self.filepath, "w") as f:
                f.write(f"# Host list created: {datetime.now().isoformat()}\n")
                f.write("# One hostname or IP address per line\n")
                f.write("#\n")

                if hosts:
                    for host in hosts:
                        if host and not host.startswith("#"):
                            f.write(f"{host.strip()}\n")

            return True
        except Exception as e:
            print(f"Error creating hostfile: {e}")
            return False

    def read_hosts(
        self, skip_comments: bool = True, strip_whitespace: bool = True
    ) -> List[str]:
        """
        Read hosts from the file.

        Args:
            skip_comments: Skip lines starting with #
            strip_whitespace: Remove leading/trailing whitespace

        Returns:
            List of hostnames/IPs
        """
        if not self.filepath.exists():
            return []

        hosts = []

        try:
            with open(self.filepath, "r") as f:
                for line in f:
                    line = line.strip() if strip_whitespace else line.rstrip("\n")

                    # Skip empty lines
                    if not line:
                        continue

                    # Skip comments
                    if skip_comments and line.startswith("#"):
                        continue

                    hosts.append(line)

            self._hosts_cache = set(hosts)
            return hosts

        except Exception as e:
            print(f"Error reading hostfile: {e}")
            return []

    def get_host_count(self) -> int:
        """
        Get count of hosts in file.

        Returns:
            Number of hosts (excluding comments)
        """
        return len(self.read_hosts())

    def has_host(self, host: str) -> bool:
        """
        Check if host exists in file.

        Args:
            host: Hostname or IP to check

        Returns:
            True if host exists
        """
        if self._hosts_cache is None:
            self.read_hosts()

        return host.strip() in self._hosts_cache

    def add_host(self, host: str, check_duplicate: bool = True) -> bool:
        """
        Add a host to the file.

        Args:
            host: Hostname or IP to add
            check_duplicate: Skip if host already exists

        Returns:
            True if added successfully
        """
        host = host.strip()

        if check_duplicate and self.has_host(host):
            return True  # Already exists

        try:
            if self.auto_backup:
                self.backup()

            with open(self.filepath, "a") as f:
                f.write(f"{host}\n")

            if self._hosts_cache is not None:
                self._hosts_cache.add(host)

            return True

        except Exception as e:
            print(f"Error adding host: {e}")
            return False

    def remove_host(self, host: str) -> bool:
        """
        Remove a host from the file.

        Args:
            host: Hostname or IP to remove

        Returns:
            True if removed successfully (or didn't exist)
        """
        host = host.strip()

        if not self.has_host(host):
            return True  # Doesn't exist, consider success

        try:
            if self.auto_backup:
                self.backup()

            # Read all lines
            with open(self.filepath, "r") as f:
                lines = f.readlines()

            # Write back without the removed host
            with open(self.filepath, "w") as f:
                for line in lines:
                    stripped = line.strip()
                    if stripped and stripped != host:
                        f.write(line)

            # Update cache
            if self._hosts_cache is not None:
                self._hosts_cache.discard(host)

            return True

        except Exception as e:
            print(f"Error removing host: {e}")
            return False

    def remove_hosts(self, hosts: List[str]) -> int:
        """
        Remove multiple hosts from the file.

        Args:
            hosts: List of hostnames/IPs to remove

        Returns:
            Number of hosts successfully removed
        """
        if not hosts:
            return 0

        hosts_to_remove = set(h.strip() for h in hosts)

        try:
            if self.auto_backup:
                self.backup()

            # Read all lines
            with open(self.filepath, "r") as f:
                lines = f.readlines()

            # Write back without the removed hosts
            removed_count = 0
            with open(self.filepath, "w") as f:
                for line in lines:
                    stripped = line.strip()
                    if stripped and stripped in hosts_to_remove:
                        removed_count += 1
                    else:
                        f.write(line)

            # Update cache
            if self._hosts_cache is not None:
                self._hosts_cache -= hosts_to_remove

            return removed_count

        except Exception as e:
            print(f"Error removing hosts: {e}")
            return 0

    def process_hosts(
        self,
        callback: Callable[[str], bool],
        remove_on_success: bool = True,
        stop_on_error: bool = False,
    ) -> tuple[int, int]:
        """
        Process each host with a callback function.

        Args:
            callback: Function to call for each host, returns True on success
            remove_on_success: Remove host from file if callback succeeds
            stop_on_error: Stop processing on first error

        Returns:
            Tuple of (success_count, fail_count)
        """
        hosts = self.read_hosts()

        if not hosts:
            return 0, 0

        success_count = 0
        fail_count = 0
        successful_hosts = []

        for host in hosts:
            try:
                if callback(host):
                    success_count += 1
                    if remove_on_success:
                        successful_hosts.append(host)
                else:
                    fail_count += 1
                    if stop_on_error:
                        break
            except Exception as e:
                print(f"Error processing {host}: {e}")
                fail_count += 1
                if stop_on_error:
                    break

        # Remove successful hosts
        if remove_on_success and successful_hosts:
            self.remove_hosts(successful_hosts)

        return success_count, fail_count

    def backup(self, suffix: Optional[str] = None) -> Optional[Path]:
        """
        Create a backup of the hostfile.

        Args:
            suffix: Backup filename suffix (default: timestamp)

        Returns:
            Path to backup file or None on error
        """
        if not self.filepath.exists():
            return None

        try:
            if suffix is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                suffix = f".{timestamp}.bak"

            backup_path = self.filepath.with_suffix(self.filepath.suffix + suffix)
            shutil.copy2(self.filepath, backup_path)

            return backup_path

        except Exception as e:
            print(f"Error creating backup: {e}")
            return None

    def restore(self, backup_path: str) -> bool:
        """
        Restore hostfile from a backup.

        Args:
            backup_path: Path to backup file

        Returns:
            True if restored successfully
        """
        backup_path = Path(backup_path)

        if not backup_path.exists():
            print(f"Backup file not found: {backup_path}")
            return False

        try:
            shutil.copy2(backup_path, self.filepath)
            self._hosts_cache = None  # Clear cache
            return True

        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False

    def list_backups(self) -> List[Path]:
        """
        List available backup files.

        Returns:
            List of backup file paths
        """
        if not self.filepath.parent.exists():
            return []

        pattern = f"{self.filepath.name}.*.bak"
        return sorted(self.filepath.parent.glob(pattern), reverse=True)

    def clear(self, keep_comments: bool = True) -> bool:
        """
        Clear all hosts from the file.

        Args:
            keep_comments: Preserve comment lines

        Returns:
            True if cleared successfully
        """
        try:
            if self.auto_backup:
                self.backup()

            if keep_comments:
                # Read and keep only comments
                with open(self.filepath, "r") as f:
                    lines = f.readlines()

                with open(self.filepath, "w") as f:
                    for line in lines:
                        if line.strip().startswith("#") or not line.strip():
                            f.write(line)
            else:
                # Clear everything
                with open(self.filepath, "w") as f:
                    f.write(f"# Cleared: {datetime.now().isoformat()}\n")

            self._hosts_cache = set()
            return True

        except Exception as e:
            print(f"Error clearing hostfile: {e}")
            return False


def main():
    """Test and demonstrate hostfile operations."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage host files for iDRAC operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new hostfile
  %(prog)s create hosts.txt 192.168.1.100 192.168.1.101
  
  # List hosts
  %(prog)s list hosts.txt
  
  # Add a host
  %(prog)s add hosts.txt 192.168.1.102
  
  # Remove a host
  %(prog)s remove hosts.txt 192.168.1.102
  
  # Count hosts
  %(prog)s count hosts.txt
  
  # Backup hostfile
  %(prog)s backup hosts.txt
  
  # List backups
  %(prog)s backups hosts.txt
        """,
    )

    parser.add_argument(
        "command",
        choices=[
            "create",
            "list",
            "add",
            "remove",
            "count",
            "backup",
            "backups",
            "clear",
        ],
        help="Command to execute",
    )
    parser.add_argument("file", help="Path to hostfile")
    parser.add_argument("hosts", nargs="*", help="Hostname(s) or IP address(es)")
    parser.add_argument(
        "--no-backup", action="store_true", help="Disable automatic backups"
    )

    args = parser.parse_args()

    hostfile = HostFile(args.file, auto_backup=not args.no_backup)

    if args.command == "create":
        if hostfile.create(args.hosts):
            print(f"✓ Created hostfile: {args.file}")
            if args.hosts:
                print(f"  Added {len(args.hosts)} host(s)")
        else:
            print(f"✗ Failed to create hostfile")
            return 1

    elif args.command == "list":
        hosts = hostfile.read_hosts()
        if hosts:
            print(f"Hosts in {args.file}:")
            for i, host in enumerate(hosts, 1):
                print(f"  {i}. {host}")
            print(f"\nTotal: {len(hosts)} host(s)")
        else:
            print(f"No hosts in {args.file}")

    elif args.command == "add":
        if not args.hosts:
            print("Error: No hosts specified to add")
            return 1

        added = 0
        for host in args.hosts:
            if hostfile.add_host(host):
                added += 1

        print(f"✓ Added {added} host(s) to {args.file}")

    elif args.command == "remove":
        if not args.hosts:
            print("Error: No hosts specified to remove")
            return 1

        removed = hostfile.remove_hosts(args.hosts)
        print(f"✓ Removed {removed} host(s) from {args.file}")

    elif args.command == "count":
        count = hostfile.get_host_count()
        print(f"{count} host(s) in {args.file}")

    elif args.command == "backup":
        backup_path = hostfile.backup()
        if backup_path:
            print(f"✓ Created backup: {backup_path}")
        else:
            print("✗ Failed to create backup")
            return 1

    elif args.command == "backups":
        backups = hostfile.list_backups()
        if backups:
            print(f"Backups for {args.file}:")
            for i, backup in enumerate(backups, 1):
                print(f"  {i}. {backup.name}")
        else:
            print(f"No backups found for {args.file}")

    elif args.command == "clear":
        if hostfile.clear():
            print(f"✓ Cleared hosts from {args.file}")
        else:
            print("✗ Failed to clear hostfile")
            return 1

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
