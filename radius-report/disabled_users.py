#!/usr/bin/env python3
"""
FreeRADIUS Disabled Users Report

Show users that are currently disabled and report how long they've been disabled.
Users are sorted by time disabled (most recent first).

The script estimates when users were disabled by:
1. Looking for recent Auth-Type := Reject entries (if table supports timestamps)
2. Using their last successful login from radacct table
3. Showing active session information if available

Usage:
    python disabled_users.py
    python disabled_users.py --days 7       # Show users disabled in last 7 days
    python disabled_users.py --all          # Show all disabled users
    python disabled_users.py --format json  # Output as JSON
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from tabulate import tabulate
from radius_db import RadiusDB


class DisabledUsersReport:
    """Generate reports for disabled users."""

    def __init__(self, db: RadiusDB):
        self.db = db

    def get_disabled_users(self, days: Optional[int] = None) -> List[Dict]:
        """
        Get list of currently disabled users with activity information.

        Args:
            days: Only show users disabled within this many days (None = all)

        Returns:
            List of dictionaries with user information
        """
        # Query to get disabled users with their last known activity
        query = """
            WITH disabled_users AS (
                SELECT DISTINCT username
                FROM radcheck
                WHERE attribute = 'Auth-Type' AND value = 'Reject'
            ),
            user_activity AS (
                SELECT 
                    username,
                    MAX(acctstarttime) as last_login,
                    MAX(acctstoptime) as last_logout,
                    COUNT(*) as total_sessions,
                    SUM(COALESCE(acctinputoctets, 0) + COALESCE(acctoutputoctets, 0)) as total_bytes
                FROM radacct
                GROUP BY username
            )
            SELECT 
                du.username,
                ua.last_login,
                ua.last_logout,
                ua.total_sessions as session_count,
                ua.total_bytes,
                CASE 
                    WHEN ua.last_logout IS NOT NULL THEN ua.last_logout
                    WHEN ua.last_login IS NOT NULL THEN ua.last_login
                    ELSE NULL
                END as estimated_disabled_time,
                CASE
                    WHEN ua.last_logout IS NOT NULL THEN 
                        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ua.last_logout)) / 86400
                    WHEN ua.last_login IS NOT NULL THEN 
                        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ua.last_login)) / 86400
                    ELSE NULL
                END as days_disabled
            FROM disabled_users du
            LEFT JOIN user_activity ua ON du.username = ua.username
            ORDER BY estimated_disabled_time DESC NULLS LAST
        """

        try:
            results = self.db.execute_query(query)

            # Filter by days if specified
            if days is not None:
                filtered = []
                for user in results:
                    if user["days_disabled"] is not None:
                        if user["days_disabled"] <= days:
                            filtered.append(user)
                    else:
                        # Include users with no activity data if within time window
                        filtered.append(user)
                results = filtered

            return results
        except Exception as e:
            print(f"✗ Error getting disabled users: {e}")
            return []

    def get_disabled_user_details(self, username: str) -> Optional[Dict]:
        """
        Get detailed information about a specific disabled user.

        Args:
            username: Username to lookup

        Returns:
            Dictionary with detailed user information
        """
        # Check if user is disabled
        check_query = """
            SELECT id, attribute, op, value
            FROM radcheck
            WHERE username = %s AND attribute = 'Auth-Type' AND value = 'Reject'
        """

        disabled_check = self.db.execute_query(check_query, (username,))
        if not disabled_check:
            return None

        # Get all user attributes
        attrs_query = """
            SELECT attribute, op, value
            FROM radcheck
            WHERE username = %s
            ORDER BY attribute
        """
        attributes = self.db.execute_query(attrs_query, (username,))

        # Get recent session history
        sessions_query = """
            SELECT 
                acctstarttime,
                acctstoptime,
                acctsessiontime,
                nasipaddress,
                framedipaddress,
                callingstationid
            FROM radacct
            WHERE username = %s
            ORDER BY acctstarttime DESC
            LIMIT 10
        """
        sessions = self.db.execute_query(sessions_query, (username,))

        # Get session statistics
        stats_query = """
            SELECT 
                COUNT(*) as total_sessions,
                SUM(COALESCE(acctinputoctets, 0) + COALESCE(acctoutputoctets, 0)) as total_bytes,
                SUM(COALESCE(acctsessiontime, 0)) as total_time,
                MAX(acctstarttime) as last_login,
                MAX(acctstoptime) as last_logout
            FROM radacct
            WHERE username = %s
        """
        stats = self.db.execute_query(stats_query, (username,))

        return {
            "username": username,
            "attributes": attributes,
            "sessions": sessions,
            "stats": stats[0] if stats else {},
        }

    def display_disabled_users_table(self, users: List[Dict]):
        """Display disabled users in a formatted table."""
        if not users:
            print("No disabled users found")
            return

        headers = [
            "Username",
            "Days Disabled",
            "Last Activity",
            "Sessions",
            "Total Data (MB)",
            "Status",
        ]

        rows = []
        for user in users:
            # Calculate days disabled
            days_disabled = user["days_disabled"]
            if days_disabled is not None:
                if days_disabled < 1:
                    days_str = f"{days_disabled * 24:.1f}h"
                else:
                    days_str = f"{days_disabled:.1f}d"
            else:
                days_str = "Unknown"

            # Last activity
            last_activity = user["estimated_disabled_time"]
            if last_activity:
                last_activity_str = str(last_activity)[:19]
            else:
                last_activity_str = "Never logged in"

            # Total data in MB
            total_mb = (user["total_bytes"] or 0) / (1024**2)

            # Status indicator
            if days_disabled is None:
                status = "📍 No history"
            elif days_disabled < 1:
                status = "🆕 Recent"
            elif days_disabled < 30:
                status = "⚠️ Active"
            else:
                status = "⏳ Old"

            rows.append(
                [
                    user["username"],
                    days_str,
                    last_activity_str,
                    user["session_count"] or 0,
                    f"{total_mb:.1f}",
                    status,
                ]
            )

        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print(f"\nTotal disabled users: {len(users)}")

        # Summary statistics
        with_history = [u for u in users if u["days_disabled"] is not None]
        if with_history:
            avg_days = sum(u["days_disabled"] for u in with_history) / len(with_history)
            recent = sum(1 for u in with_history if u["days_disabled"] < 7)
            old = sum(1 for u in with_history if u["days_disabled"] >= 30)

            print(f"\nSummary:")
            print(f"  Average days disabled: {avg_days:.1f}")
            print(f"  Recently disabled (<7 days): {recent}")
            print(f"  Long-term disabled (≥30 days): {old}")

    def display_user_details(self, details: Dict):
        """Display detailed information about a disabled user."""
        print(f"\n{'='*70}")
        print(f"Disabled User Details: {details['username']}")
        print(f"{'='*70}")

        # Attributes
        print("\nAttributes:")
        for attr in details["attributes"]:
            value = attr["value"]
            if "Password" in attr["attribute"]:
                value = "****" + value[-4:] if len(value) > 4 else "****"
            print(f"  {attr['attribute']} {attr['op']} {value}")

        # Statistics
        stats = details["stats"]
        if stats and stats.get("total_sessions"):
            print("\nUsage Statistics:")
            print(f"  Total Sessions: {stats['total_sessions']}")
            print(
                f"  Total Time: {stats['total_time'] / 3600:.1f} hours"
                if stats["total_time"]
                else "  Total Time: 0 hours"
            )
            print(
                f"  Total Data: {stats['total_bytes'] / (1024**2):.1f} MB"
                if stats["total_bytes"]
                else "  Total Data: 0 MB"
            )
            print(
                f"  Last Login: {str(stats['last_login'])[:19] if stats['last_login'] else 'Never'}"
            )
            print(
                f"  Last Logout: {str(stats['last_logout'])[:19] if stats['last_logout'] else 'N/A'}"
            )
        else:
            print("\nNo usage statistics available")

        # Recent sessions
        sessions = details["sessions"]
        if sessions:
            print(f"\nRecent Sessions (last {len(sessions)}):")
            session_headers = [
                "Start Time",
                "Stop Time",
                "Duration",
                "NAS IP",
                "User IP",
            ]
            session_rows = []

            for session in sessions:
                duration = session["acctsessiontime"]
                duration_str = (
                    f"{duration // 3600}h {(duration % 3600) // 60}m"
                    if duration
                    else "-"
                )

                session_rows.append(
                    [
                        (
                            str(session["acctstarttime"])[:19]
                            if session["acctstarttime"]
                            else "-"
                        ),
                        (
                            str(session["acctstoptime"])[:19]
                            if session["acctstoptime"]
                            else "Active"
                        ),
                        duration_str,
                        session["nasipaddress"] or "-",
                        session["framedipaddress"] or "-",
                    ]
                )

            print(tabulate(session_rows, headers=session_headers, tablefmt="simple"))
        else:
            print("\nNo session history available")


def main():
    parser = argparse.ArgumentParser(
        description="FreeRADIUS Disabled Users Report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all disabled users
  %(prog)s

  # Show users disabled in the last 7 days
  %(prog)s --days 7

  # Show users disabled in the last 30 days
  %(prog)s --days 30

  # Show all disabled users (explicit)
  %(prog)s --all

  # Get details about a specific disabled user
  %(prog)s --username john

  # Output as JSON
  %(prog)s --format json

  # Output as CSV
  %(prog)s --format csv
        """,
    )

    parser.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="Show only users disabled within last N days",
    )
    parser.add_argument(
        "--all", action="store_true", help="Show all disabled users (default behavior)"
    )
    parser.add_argument(
        "--username", metavar="USER", help="Show detailed information for specific user"
    )
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )

    args = parser.parse_args()

    try:
        db = RadiusDB()
        report = DisabledUsersReport(db)

        # Show details for specific user
        if args.username:
            details = report.get_disabled_user_details(args.username)
            if details:
                report.display_user_details(details)
            else:
                print(f"✗ User '{args.username}' is not disabled or does not exist")
                sys.exit(1)
        else:
            # Get disabled users list
            days = args.days if args.days else None
            users = report.get_disabled_users(days=days)

            if args.format == "json":
                # Convert datetime objects to strings for JSON serialization
                for user in users:
                    for key, value in user.items():
                        if isinstance(value, datetime):
                            user[key] = str(value)
                print(json.dumps(users, indent=2, default=str))

            elif args.format == "csv":
                if users:
                    # Print CSV header
                    print(
                        "username,days_disabled,last_activity,session_count,total_bytes"
                    )
                    for user in users:
                        print(
                            f"{user['username']},"
                            f"{user['days_disabled'] or 'Unknown'},"
                            f"{user['estimated_disabled_time'] or 'Never'},"
                            f"{user['session_count'] or 0},"
                            f"{user['total_bytes'] or 0}"
                        )

            else:  # table format
                report.display_disabled_users_table(users)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
