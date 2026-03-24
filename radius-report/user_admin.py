#!/usr/bin/env python3
"""
FreeRADIUS User Administration Script

Manage user accounts in the FreeRADIUS PostgreSQL database.
Supports add, remove, enable, disable, lookup, list, and stats operations.

Usage:
    python user_admin.py add --username john --password secret123
    python user_admin.py remove --username john
    python user_admin.py disable --username john
    python user_admin.py enable --username john
    python user_admin.py lookup --username john
    python user_admin.py list
    python user_admin.py stats
"""

import argparse
import sys
import hashlib
from datetime import datetime
from typing import Optional, Dict, List
from tabulate import tabulate
from radius_db import RadiusDB


class UserAdmin:
    """User administration operations."""

    def __init__(self, db: RadiusDB):
        self.db = db

    def add_user(
        self,
        username: str,
        password: str,
        password_type: str = "Cleartext-Password",
        disabled: bool = False,
    ) -> bool:
        """
        Add a new user to the database.

        Args:
            username: Username
            password: User password
            password_type: Password attribute type (default: Cleartext-Password)
            disabled: Whether user starts disabled

        Returns:
            True if successful, False otherwise
        """
        # Check if user already exists
        existing = self.lookup_user(username)
        if existing:
            print(f"✗ User '{username}' already exists")
            return False

        # Hash password if needed
        if password_type == "Crypt-Password":
            import crypt

            password = crypt.crypt(password)
        elif password_type == "MD5-Password":
            password = hashlib.md5(password.encode()).hexdigest()

        # Insert into radcheck table
        query = """
            INSERT INTO radcheck (username, attribute, op, value)
            VALUES (%s, %s, ':=', %s)
        """

        try:
            # Add password
            rows = self.db.execute_update(query, (username, password_type, password))

            # Add disabled flag if needed
            if disabled:
                self.db.execute_update(query, (username, "Auth-Type", "Reject"))

            if rows > 0:
                status = "(disabled)" if disabled else "(enabled)"
                print(f"✓ Successfully added user '{username}' {status}")
                return True
            else:
                print(f"✗ Failed to add user '{username}'")
                return False

        except Exception as e:
            print(f"✗ Error adding user: {e}")
            return False

    def remove_user(self, username: str) -> bool:
        """
        Remove a user from the database.

        Args:
            username: Username to remove

        Returns:
            True if successful, False otherwise
        """
        # Check if user exists
        existing = self.lookup_user(username)
        if not existing:
            print(f"✗ User '{username}' not found")
            return False

        try:
            # Delete from radcheck
            rows1 = self.db.execute_update(
                "DELETE FROM radcheck WHERE username = %s", (username,)
            )

            # Delete from radreply
            rows2 = self.db.execute_update(
                "DELETE FROM radreply WHERE username = %s", (username,)
            )

            # Delete from radusergroup
            rows3 = self.db.execute_update(
                "DELETE FROM radusergroup WHERE username = %s", (username,)
            )

            total_rows = rows1 + rows2 + rows3

            if total_rows > 0:
                print(
                    f"✓ Successfully removed user '{username}' ({total_rows} records)"
                )
                return True
            else:
                print(f"✗ Failed to remove user '{username}'")
                return False

        except Exception as e:
            print(f"✗ Error removing user: {e}")
            return False

    def disable_user(self, username: str) -> bool:
        """
        Disable a user account.

        Args:
            username: Username to disable

        Returns:
            True if successful, False otherwise
        """
        # Check if user exists
        existing = self.lookup_user(username)
        if not existing:
            print(f"✗ User '{username}' not found")
            return False

        # Check if already disabled
        query = """
            SELECT id FROM radcheck 
            WHERE username = %s AND attribute = 'Auth-Type' AND value = 'Reject'
        """
        if self.db.execute_query(query, (username,)):
            print(f"⚠ User '{username}' is already disabled")
            return True

        # Add Auth-Type := Reject
        query = """
            INSERT INTO radcheck (username, attribute, op, value)
            VALUES (%s, 'Auth-Type', ':=', 'Reject')
        """

        try:
            rows = self.db.execute_update(query, (username,))

            if rows > 0:
                print(f"✓ Successfully disabled user '{username}'")
                return True
            else:
                print(f"✗ Failed to disable user '{username}'")
                return False

        except Exception as e:
            print(f"✗ Error disabling user: {e}")
            return False

    def enable_user(self, username: str) -> bool:
        """
        Enable a previously disabled user account.

        Args:
            username: Username to enable

        Returns:
            True if successful, False otherwise
        """
        # Check if user exists
        existing = self.lookup_user(username)
        if not existing:
            print(f"✗ User '{username}' not found")
            return False

        # Remove Auth-Type := Reject
        query = """
            DELETE FROM radcheck 
            WHERE username = %s AND attribute = 'Auth-Type' AND value = 'Reject'
        """

        try:
            rows = self.db.execute_update(query, (username,))

            if rows > 0:
                print(f"✓ Successfully enabled user '{username}'")
                return True
            else:
                print(f"⚠ User '{username}' was not disabled")
                return True

        except Exception as e:
            print(f"✗ Error enabling user: {e}")
            return False

    def lookup_user(self, username: str) -> Optional[Dict]:
        """
        Lookup a specific user.

        Args:
            username: Username to lookup

        Returns:
            Dictionary with user details or None if not found
        """
        query = """
            SELECT username, attribute, op, value
            FROM radcheck 
            WHERE username = %s
            ORDER BY attribute
        """

        try:
            results = self.db.execute_query(query, (username,))
            if not results:
                return None

            # Consolidate user attributes
            user_info = {
                "username": username,
                "attributes": results,
                "disabled": any(
                    r["attribute"] == "Auth-Type" and r["value"] == "Reject"
                    for r in results
                ),
            }

            return user_info
        except Exception as e:
            print(f"✗ Error looking up user: {e}")
            return None

    def list_users(
        self, include_disabled: bool = True, disabled_only: bool = False
    ) -> List[Dict]:
        """
        List all users.

        Args:
            include_disabled: Include disabled users in results
            disabled_only: Show only disabled users

        Returns:
            List of user dictionaries
        """
        query = """
            SELECT DISTINCT username
            FROM radcheck
            WHERE attribute != 'Auth-Type' OR value != 'Reject'
            ORDER BY username
        """

        if disabled_only:
            query = """
                SELECT DISTINCT username
                FROM radcheck
                WHERE attribute = 'Auth-Type' AND value = 'Reject'
                ORDER BY username
            """

        try:
            results = self.db.execute_query(query)

            user_list = []
            for row in results:
                username = row["username"]
                user_info = self.lookup_user(username)
                if user_info:
                    if disabled_only:
                        if user_info["disabled"]:
                            user_list.append(user_info)
                    elif include_disabled:
                        user_list.append(user_info)
                    elif not user_info["disabled"]:
                        user_list.append(user_info)

            return user_list
        except Exception as e:
            print(f"✗ Error listing users: {e}")
            return []

    def get_user_stats(self) -> List[Dict]:
        """
        Get usage statistics for users from accounting data.

        Returns:
            List of dictionaries with user statistics
        """
        query = """
            SELECT 
                rc.username,
                CASE WHEN rc2.id IS NOT NULL THEN 'Disabled' ELSE 'Enabled' END as status,
                COUNT(ra.radacctid) as total_sessions,
                COUNT(CASE WHEN ra.acctstoptime IS NULL THEN 1 END) as active_sessions,
                SUM(COALESCE(ra.acctsessiontime, 0)) as total_time_seconds,
                SUM(COALESCE(ra.acctinputoctets, 0) + COALESCE(ra.acctoutputoctets, 0)) as total_bytes,
                MAX(ra.acctstarttime) as last_login,
                MAX(ra.acctstoptime) as last_logout
            FROM radcheck rc
            LEFT JOIN radacct ra ON rc.username = ra.username
            LEFT JOIN radcheck rc2 ON rc.username = rc2.username 
                AND rc2.attribute = 'Auth-Type' AND rc2.value = 'Reject'
            WHERE rc.attribute IN ('Cleartext-Password', 'Crypt-Password', 'MD5-Password', 'User-Password')
            GROUP BY rc.username, rc2.id
            ORDER BY total_sessions DESC
        """

        try:
            return self.db.execute_query(query)
        except Exception as e:
            print(f"✗ Error getting user stats: {e}")
            return []

    def display_user_list(self, user_list: List[Dict]):
        """Display user list in a formatted table."""
        if not user_list:
            print("No users found")
            return

        headers = ["Username", "Status", "Password Type"]
        rows = []

        for user in user_list:
            status = "Disabled" if user["disabled"] else "Enabled"

            # Find password attribute type
            pwd_attr = "-"
            for attr in user["attributes"]:
                if "Password" in attr["attribute"]:
                    pwd_attr = attr["attribute"]
                    break

            rows.append([user["username"], status, pwd_attr])

        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal users: {len(user_list)}")

    def display_user_stats(self, stats: List[Dict]):
        """Display user statistics in a formatted table."""
        if not stats:
            print("No user statistics available")
            return

        headers = [
            "Username",
            "Status",
            "Total Sessions",
            "Active",
            "Total Time",
            "Data (GB)",
            "Last Login",
            "Last Logout",
        ]

        rows = []
        for stat in stats:
            # Convert seconds to hours
            total_hours = (stat["total_time_seconds"] or 0) / 3600

            # Convert bytes to GB
            total_gb = (stat["total_bytes"] or 0) / (1024**3)

            row = [
                stat["username"],
                stat["status"],
                stat["total_sessions"] or 0,
                stat["active_sessions"] or 0,
                f"{total_hours:.1f}h",
                f"{total_gb:.2f}",
                str(stat["last_login"])[:19] if stat["last_login"] else "-",
                str(stat["last_logout"])[:19] if stat["last_logout"] else "-",
            ]
            rows.append(row)

        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal users: {len(stats)}")


def main():
    parser = argparse.ArgumentParser(
        description="FreeRADIUS User Administration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a new user
  %(prog)s add --username john --password secret123

  # Add a disabled user
  %(prog)s add --username jane --password pass456 --disabled

  # Disable a user
  %(prog)s disable --username john

  # Enable a user
  %(prog)s enable --username john

  # Lookup specific user
  %(prog)s lookup --username john

  # List all users
  %(prog)s list

  # List only enabled users
  %(prog)s list --no-disabled

  # List only disabled users
  %(prog)s list --disabled-only

  # Remove a user
  %(prog)s remove --username john

  # Show user usage statistics
  %(prog)s stats
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new user")
    add_parser.add_argument("--username", required=True, help="Username")
    add_parser.add_argument("--password", required=True, help="Password")
    add_parser.add_argument(
        "--password-type",
        default="Cleartext-Password",
        choices=["Cleartext-Password", "Crypt-Password", "MD5-Password"],
        help="Password storage type (default: Cleartext-Password)",
    )
    add_parser.add_argument(
        "--disabled", action="store_true", help="Create user in disabled state"
    )

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a user")
    remove_parser.add_argument("--username", required=True, help="Username to remove")

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable a user")
    disable_parser.add_argument("--username", required=True, help="Username to disable")

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable a user")
    enable_parser.add_argument("--username", required=True, help="Username to enable")

    # Lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Lookup a specific user")
    lookup_parser.add_argument("--username", required=True, help="Username to lookup")

    # List command
    list_parser = subparsers.add_parser("list", help="List all users")
    list_parser.add_argument(
        "--no-disabled", action="store_true", help="Exclude disabled users"
    )
    list_parser.add_argument(
        "--disabled-only", action="store_true", help="Show only disabled users"
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show user usage statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        db = RadiusDB()
        admin = UserAdmin(db)

        if args.command == "add":
            admin.add_user(
                username=args.username,
                password=args.password,
                password_type=args.password_type,
                disabled=args.disabled,
            )

        elif args.command == "remove":
            admin.remove_user(args.username)

        elif args.command == "disable":
            admin.disable_user(args.username)

        elif args.command == "enable":
            admin.enable_user(args.username)

        elif args.command == "lookup":
            user = admin.lookup_user(args.username)
            if user:
                print(f"\nUser Details:")
                print(f"  Username: {user['username']}")
                print(f"  Status: {'Disabled' if user['disabled'] else 'Enabled'}")
                print(f"\n  Attributes:")
                for attr in user["attributes"]:
                    # Mask password values
                    value = attr["value"]
                    if "Password" in attr["attribute"]:
                        value = "****" + value[-4:] if len(value) > 4 else "****"
                    print(f"    {attr['attribute']} {attr['op']} {value}")
            else:
                print(f"✗ User '{args.username}' not found")

        elif args.command == "list":
            include_disabled = not args.no_disabled
            user_list = admin.list_users(
                include_disabled=include_disabled, disabled_only=args.disabled_only
            )
            admin.display_user_list(user_list)

        elif args.command == "stats":
            stats = admin.get_user_stats()
            admin.display_user_stats(stats)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
