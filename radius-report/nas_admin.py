#!/usr/bin/env python3
"""
FreeRADIUS NAS (Network Access Server) Administration Script

Manage NAS entries in the FreeRADIUS PostgreSQL database.
Supports add, remove, lookup, list, and stats operations.

Usage:
    python nas_admin.py add --nasname switch1.example.com --shortname switch1 \\
                            --secret secretkey123 --server 192.168.1.1
    python nas_admin.py remove --nasname switch1.example.com
    python nas_admin.py lookup --nasname switch1.example.com
    python nas_admin.py list
    python nas_admin.py stats
"""

import argparse
import sys
from typing import Optional, Dict, List
from tabulate import tabulate
from radius_db import RadiusDB


class NASAdmin:
    """NAS administration operations."""

    def __init__(self, db: RadiusDB):
        self.db = db

    def add_nas(
        self,
        nasname: str,
        shortname: str,
        secret: str,
        server: Optional[str] = None,
        ports: Optional[int] = None,
        type_: str = "other",
        description: Optional[str] = None,
    ) -> bool:
        """
        Add a new NAS entry to the database.

        Args:
            nasname: Fully qualified hostname or IP of the NAS
            shortname: Short name identifier
            secret: RADIUS shared secret
            server: NAS server IP (optional)
            ports: Number of ports (optional)
            type_: NAS type (default: "other")
            description: Optional description

        Returns:
            True if successful, False otherwise
        """
        # Check if NAS already exists
        existing = self.lookup_nas(nasname)
        if existing:
            print(f"✗ NAS '{nasname}' already exists")
            return False

        query = """
            INSERT INTO nas (nasname, shortname, secret, server, ports, type, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        try:
            rows = self.db.execute_update(
                query, (nasname, shortname, secret, server, ports, type_, description)
            )

            if rows > 0:
                print(f"✓ Successfully added NAS '{nasname}'")
                return True
            else:
                print(f"✗ Failed to add NAS '{nasname}'")
                return False

        except Exception as e:
            print(f"✗ Error adding NAS: {e}")
            return False

    def remove_nas(self, nasname: str) -> bool:
        """
        Remove a NAS entry from the database.

        Args:
            nasname: NAS name to remove

        Returns:
            True if successful, False otherwise
        """
        # Check if NAS exists
        existing = self.lookup_nas(nasname)
        if not existing:
            print(f"✗ NAS '{nasname}' not found")
            return False

        query = "DELETE FROM nas WHERE nasname = %s"

        try:
            rows = self.db.execute_update(query, (nasname,))

            if rows > 0:
                print(f"✓ Successfully removed NAS '{nasname}'")
                return True
            else:
                print(f"✗ Failed to remove NAS '{nasname}'")
                return False

        except Exception as e:
            print(f"✗ Error removing NAS: {e}")
            return False

    def lookup_nas(self, nasname: str) -> Optional[Dict]:
        """
        Lookup a specific NAS by name.

        Args:
            nasname: NAS name to lookup

        Returns:
            Dictionary with NAS details or None if not found
        """
        query = """
            SELECT id, nasname, shortname, type, ports, 
                   secret, server, community, description
            FROM nas 
            WHERE nasname = %s
        """

        try:
            results = self.db.execute_query(query, (nasname,))
            return results[0] if results else None
        except Exception as e:
            print(f"✗ Error looking up NAS: {e}")
            return None

    def list_nas(self, show_secrets: bool = False) -> List[Dict]:
        """
        List all NAS entries.

        Args:
            show_secrets: Whether to display shared secrets

        Returns:
            List of NAS dictionaries
        """
        query = """
            SELECT id, nasname, shortname, type, ports, 
                   secret, server, description
            FROM nas 
            ORDER BY nasname
        """

        try:
            results = self.db.execute_query(query)

            # Optionally mask secrets
            if not show_secrets:
                for nas in results:
                    if nas["secret"]:
                        nas["secret"] = (
                            "****" + nas["secret"][-4:]
                            if len(nas["secret"]) > 4
                            else "****"
                        )

            return results
        except Exception as e:
            print(f"✗ Error listing NAS: {e}")
            return []

    def get_nas_stats(self) -> Dict:
        """
        Get statistics about NAS usage from accounting data.

        Returns:
            Dictionary with NAS statistics
        """
        query = """
            SELECT 
                n.nasname,
                n.shortname,
                n.type,
                COUNT(DISTINCT a.username) as unique_users,
                COUNT(*) as total_sessions,
                COUNT(CASE WHEN a.acctstoptime IS NULL THEN 1 END) as active_sessions,
                SUM(COALESCE(a.acctinputoctets, 0) + COALESCE(a.acctoutputoctets, 0)) as total_bytes,
                MAX(a.acctstarttime) as last_session
            FROM nas n
            LEFT JOIN radacct a ON n.nasname = a.nasipaddress OR n.nasname = a.nasportid
            GROUP BY n.id, n.nasname, n.shortname, n.type
            ORDER BY total_sessions DESC
        """

        try:
            return self.db.execute_query(query)
        except Exception as e:
            print(f"✗ Error getting NAS stats: {e}")
            return []

    def display_nas_list(self, nas_list: List[Dict], show_secrets: bool = False):
        """Display NAS list in a formatted table."""
        if not nas_list:
            print("No NAS entries found")
            return

        headers = ["ID", "NAS Name", "Short Name", "Type", "Server", "Ports"]
        if show_secrets:
            headers.append("Secret")
        headers.append("Description")

        rows = []
        for nas in nas_list:
            row = [
                nas["id"],
                nas["nasname"],
                nas["shortname"],
                nas["type"] or "-",
                nas["server"] or "-",
                nas["ports"] or "-",
            ]
            if show_secrets:
                row.append(nas["secret"] or "-")
            row.append(nas["description"] or "-")
            rows.append(row)

        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal NAS entries: {len(nas_list)}")

    def display_nas_stats(self, stats: List[Dict]):
        """Display NAS statistics in a formatted table."""
        if not stats:
            print("No NAS statistics available")
            return

        headers = [
            "NAS Name",
            "Short Name",
            "Type",
            "Unique Users",
            "Total Sessions",
            "Active Sessions",
            "Total Data (GB)",
            "Last Session",
        ]

        rows = []
        for stat in stats:
            # Convert bytes to GB
            total_gb = (stat["total_bytes"] or 0) / (1024**3)

            row = [
                stat["nasname"],
                stat["shortname"],
                stat["type"] or "-",
                stat["unique_users"] or 0,
                stat["total_sessions"] or 0,
                stat["active_sessions"] or 0,
                f"{total_gb:.2f}",
                str(stat["last_session"])[:19] if stat["last_session"] else "-",
            ]
            rows.append(row)

        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal NAS devices: {len(stats)}")


def main():
    parser = argparse.ArgumentParser(
        description="FreeRADIUS NAS Administration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a new NAS
  %(prog)s add --nasname switch1.example.com --shortname switch1 \\
               --secret mysecret123 --server 192.168.1.10 --type cisco

  # List all NAS entries
  %(prog)s list

  # List with secrets visible
  %(prog)s list --show-secrets

  # Lookup specific NAS
  %(prog)s lookup --nasname switch1.example.com

  # Remove a NAS
  %(prog)s remove --nasname switch1.example.com

  # Show NAS usage statistics
  %(prog)s stats
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new NAS")
    add_parser.add_argument("--nasname", required=True, help="NAS hostname or IP")
    add_parser.add_argument("--shortname", required=True, help="Short identifier")
    add_parser.add_argument("--secret", required=True, help="RADIUS shared secret")
    add_parser.add_argument("--server", help="NAS server IP")
    add_parser.add_argument("--ports", type=int, help="Number of ports")
    add_parser.add_argument("--type", default="other", help="NAS type (default: other)")
    add_parser.add_argument("--description", help="Optional description")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a NAS")
    remove_parser.add_argument("--nasname", required=True, help="NAS name to remove")

    # Lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Lookup a specific NAS")
    lookup_parser.add_argument("--nasname", required=True, help="NAS name to lookup")

    # List command
    list_parser = subparsers.add_parser("list", help="List all NAS entries")
    list_parser.add_argument(
        "--show-secrets", action="store_true", help="Show RADIUS shared secrets"
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show NAS usage statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        db = RadiusDB()
        admin = NASAdmin(db)

        if args.command == "add":
            admin.add_nas(
                nasname=args.nasname,
                shortname=args.shortname,
                secret=args.secret,
                server=args.server,
                ports=args.ports,
                type_=args.type,
                description=args.description,
            )

        elif args.command == "remove":
            admin.remove_nas(args.nasname)

        elif args.command == "lookup":
            nas = admin.lookup_nas(args.nasname)
            if nas:
                print(f"\nNAS Details:")
                print(f"  ID: {nas['id']}")
                print(f"  NAS Name: {nas['nasname']}")
                print(f"  Short Name: {nas['shortname']}")
                print(f"  Type: {nas['type'] or '-'}")
                print(f"  Server: {nas['server'] or '-'}")
                print(f"  Ports: {nas['ports'] or '-'}")
                print(f"  Secret: {'*' * len(nas['secret']) if nas['secret'] else '-'}")
                print(f"  Description: {nas['description'] or '-'}")
            else:
                print(f"✗ NAS '{args.nasname}' not found")

        elif args.command == "list":
            nas_list = admin.list_nas(show_secrets=args.show_secrets)
            admin.display_nas_list(nas_list, show_secrets=args.show_secrets)

        elif args.command == "stats":
            stats = admin.get_nas_stats()
            admin.display_nas_stats(stats)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
