#!/usr/bin/env python3
"""
Display change report for a specific data directory.
"""

import argparse
import re
import sys
from pathlib import Path
import pandas as pd


def extract_date_from_directory(data_dir: str) -> str:
    """
    Extract date from data directory name (e.g., 'data-2025-12-26' -> '2025-12-26')

    Args:
        data_dir: Directory name or path

    Returns:
        Date string in YYYY-MM-DD format

    Raises:
        ValueError: If date cannot be extracted
    """
    match = re.search(r"(\d{4}-\d{2}-\d{2})", data_dir)
    if not match:
        raise ValueError(f"Could not extract date from directory: {data_dir}")
    return match.group(1)


def find_change_report(data_dir: str) -> Path:
    """
    Find the change report parquet file in the specified directory

    Args:
        data_dir: Directory name or path

    Returns:
        Path to the change report file

    Raises:
        FileNotFoundError: If report file not found
    """
    dir_path = Path(data_dir)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {data_dir}")

    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {data_dir}")

    # Extract date and construct filename
    date = extract_date_from_directory(data_dir)
    report_file = dir_path / f"change_report_{date}.parquet"

    if not report_file.exists():
        raise FileNotFoundError(
            f"Change report not found: {report_file}\n"
            f"Run database_reports.py first to generate reports."
        )

    return report_file


def display_report(data_dir: str):
    """
    Display the change report for the specified data directory

    Args:
        data_dir: Directory name or path
    """
    try:
        report_file = find_change_report(data_dir)
        print(f"Reading change report: {report_file}\n")
        print("=" * 70)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Read the report
    df = pd.read_parquet(report_file)

    # Read the report
    df = pd.read_parquet(report_file)

    print("Columns:", df.columns.tolist())
    print(f"\nTotal rows: {len(df)}")
    print(f"\nChange status breakdown:")
    print(df["change_status"].value_counts())

    print("\n--- Sample of ADDED hosts ---")
    added_df = df[df["change_status"] == "added"][
        ["fqdn", "hostname", "system", "change_status"]
    ]
    if len(added_df) > 0:
        print(added_df.head())
    else:
        print("(none)")

    print("\n--- Sample of REMOVED hosts ---")
    removed_df = df[df["change_status"] == "removed"][
        ["fqdn", "hostname", "system", "change_status"]
    ]
    if len(removed_df) > 0:
        print(removed_df.head())
    else:
        print("(none)")

    print("\n--- Sample of UNCHANGED hosts ---")
    unchanged_df = df[df["change_status"] == "unchanged"][
        ["fqdn", "hostname", "system", "cpu_usage", "change_status"]
    ]
    if len(unchanged_df) > 0:
        print(unchanged_df.head())
    else:
        print("(none)")

    print("\n" + "=" * 70)


def list_available_reports():
    """
    List all available change reports in data-* directories
    """
    reports = []
    for data_dir in sorted(Path(".").glob("data-*")):
        if data_dir.is_dir():
            try:
                report_file = find_change_report(str(data_dir))
                reports.append((str(data_dir), report_file))
            except (FileNotFoundError, ValueError):
                pass

    if reports:
        print("Available change reports:")
        for data_dir, report_file in reports:
            print(f"  {data_dir}")
    else:
        print("No change reports found. Run database_reports.py first.")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Display change report for a specific data directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s data-2025-12-26
  %(prog)s data-2026-01-02
  %(prog)s --list
        """,
    )

    parser.add_argument(
        "data_dir", nargs="?", help="Data directory (e.g., data-2025-12-26)"
    )

    parser.add_argument(
        "-l", "--list", action="store_true", help="List all available change reports"
    )

    args = parser.parse_args()

    if args.list:
        list_available_reports()
        return 0

    if not args.data_dir:
        parser.print_help()
        print("\n")
        list_available_reports()
        return 1

    display_report(args.data_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
