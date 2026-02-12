#!/usr/bin/env python3
"""
Generate reports from the DuckDB database showing hosts that appear or disappear
between collection dates. Creates parquet files for each data directory with
change tracking information.
"""

from pathlib import Path
from typing import List, Dict, Tuple
import duckdb
import pandas as pd


def get_database_connection(db_path: Path = None) -> duckdb.DuckDBPyConnection:
    """
    Connect to the DuckDB database

    Args:
        db_path: Path to database file. If None, uses default location.

    Returns:
        DuckDB connection object
    """
    if db_path is None:
        script_dir = Path(__file__).parent
        db_path = script_dir / "database" / "system_metrics.duckdb"

    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. Run merge_datasets.py first."
        )

    return duckdb.connect(str(db_path), read_only=True)


def get_collection_dates(conn: duckdb.DuckDBPyConnection) -> List[str]:
    """
    Get all collection dates from the database in chronological order

    Args:
        conn: DuckDB connection

    Returns:
        List of date strings in YYYY-MM-DD format
    """
    result = conn.execute(
        """
        SELECT DISTINCT collection_date
        FROM metrics
        ORDER BY collection_date
    """
    ).fetchall()

    return [str(row[0]) for row in result]


def get_hosts_for_date(conn: duckdb.DuckDBPyConnection, collection_date: str) -> set:
    """
    Get all unique hosts (fqdn) present on a given collection date

    Args:
        conn: DuckDB connection
        collection_date: Date string in YYYY-MM-DD format

    Returns:
        Set of FQDNs
    """
    result = conn.execute(
        f"""
        SELECT DISTINCT fqdn
        FROM metrics
        WHERE collection_date = '{collection_date}'
    """
    ).fetchall()

    return {row[0] for row in result}


def get_metrics_with_host_info(
    conn: duckdb.DuckDBPyConnection, collection_date: str
) -> pd.DataFrame:
    """
    Get all metrics for a specific date with host information

    Args:
        conn: DuckDB connection
        collection_date: Date string in YYYY-MM-DD format

    Returns:
        DataFrame with metrics and host info
    """
    df = conn.execute(
        f"""
        SELECT 
            m.fqdn,
            m.hostname,
            h.system,
            h.ip_address,
            m.collection_date,
            m.cpu_usage,
            m.memory_usage,
            m.disk_usage,
            m.network_in,
            m.network_out,
            m.process_count,
            m.uptime_hours
        FROM metrics m
        JOIN hostnames h ON m.fqdn = h.fqdn
        WHERE m.collection_date = '{collection_date}'
        ORDER BY m.fqdn
    """
    ).df()

    return df


def generate_change_report(
    conn: duckdb.DuckDBPyConnection, current_date: str, previous_date: str = None
) -> pd.DataFrame:
    """
    Generate a report showing hosts that were added or removed between dates

    Args:
        conn: DuckDB connection
        current_date: Current collection date
        previous_date: Previous collection date (None for first date)

    Returns:
        DataFrame with change tracking information
    """
    # Get current metrics
    current_df = get_metrics_with_host_info(conn, current_date)
    current_hosts = set(current_df["fqdn"].unique())

    if previous_date is None:
        # First dataset - all hosts are "added"
        current_df["change_status"] = "added"
        return current_df

    # Get previous hosts
    previous_hosts = get_hosts_for_date(conn, previous_date)

    # Identify changes
    added_hosts = current_hosts - previous_hosts
    removed_hosts = previous_hosts - current_hosts

    # Mark current hosts as added or unchanged
    current_df["change_status"] = current_df["fqdn"].apply(
        lambda fqdn: "added" if fqdn in added_hosts else "unchanged"
    )

    # Create records for removed hosts (using data from previous date)
    if removed_hosts:
        removed_df = conn.execute(
            f"""
            SELECT 
                m.fqdn,
                m.hostname,
                h.system,
                h.ip_address,
                '{current_date}'::DATE as collection_date,
                NULL::DOUBLE as cpu_usage,
                NULL::DOUBLE as memory_usage,
                NULL::DOUBLE as disk_usage,
                NULL::DOUBLE as network_in,
                NULL::DOUBLE as network_out,
                NULL::INTEGER as process_count,
                NULL::DOUBLE as uptime_hours
            FROM metrics m
            JOIN hostnames h ON m.fqdn = h.fqdn
            WHERE m.collection_date = '{previous_date}'
                AND m.fqdn IN ({','.join(f"'{h}'" for h in removed_hosts)})
        """
        ).df()

        removed_df["change_status"] = "removed"

        # Combine current and removed
        result_df = pd.concat([current_df, removed_df], ignore_index=True)
    else:
        result_df = current_df

    return result_df


def generate_all_reports(output_dir: Path = None):
    """
    Generate change tracking reports for all data directories

    Args:
        output_dir: Directory to save reports. If None, saves to data-* directories.
    """
    print("=" * 70)
    print("DATABASE CHANGE TRACKING REPORT GENERATOR")
    print("=" * 70)
    print()

    # Connect to database
    conn = get_database_connection()

    try:
        # Get all collection dates
        dates = get_collection_dates(conn)

        if not dates:
            print("No data found in database. Run merge_datasets.py first.")
            return

        print(f"Found {len(dates)} collection dates: {', '.join(dates)}\n")

        # Generate report for each date
        previous_date = None

        for i, current_date in enumerate(dates, 1):
            print(f"[{i}/{len(dates)}] Processing date: {current_date}")

            # Generate change report
            report_df = generate_change_report(conn, current_date, previous_date)

            # Count changes
            added_count = (report_df["change_status"] == "added").sum()
            removed_count = (report_df["change_status"] == "removed").sum()
            unchanged_count = (report_df["change_status"] == "unchanged").sum()

            print(
                f"  📊 Added: {added_count}, Removed: {removed_count}, Unchanged: {unchanged_count}"
            )

            # Determine output location
            if output_dir:
                out_path = output_dir
                out_path.mkdir(parents=True, exist_ok=True)
            else:
                # Save to corresponding data-* directory
                out_path = Path(f"data-{current_date}")
                if not out_path.exists():
                    print(
                        f"  ⚠️  Warning: Directory {out_path} not found, using current directory"
                    )
                    out_path = Path(".")

            # Save to parquet
            output_file = out_path / f"change_report_{current_date}.parquet"
            report_df.to_parquet(output_file, index=False)
            print(f"  ✓ Saved report: {output_file}")

            # Display sample of changes if any
            if added_count > 0 or removed_count > 0:
                changes_df = report_df[report_df["change_status"] != "unchanged"]
                print(f"  🔍 Changes detected:")
                for _, row in changes_df.iterrows():
                    status_icon = "➕" if row["change_status"] == "added" else "➖"
                    print(
                        f"     {status_icon} {row['fqdn']} ({row['hostname']}) - {row['change_status']}"
                    )

            print()

            previous_date = current_date

        print("=" * 70)
        print(f"✓ Generated {len(dates)} change tracking report(s)")
        print("=" * 70)

        # Generate summary report
        generate_summary_report(conn)

    finally:
        conn.close()


def generate_summary_report(conn: duckdb.DuckDBPyConnection):
    """
    Generate a comprehensive summary of host changes over time

    Args:
        conn: DuckDB connection
    """
    print("\n" + "=" * 70)
    print("HOST LIFECYCLE SUMMARY")
    print("=" * 70)

    # Get date range analysis
    result = conn.execute(
        """
        WITH date_hosts AS (
            SELECT 
                collection_date,
                COUNT(DISTINCT fqdn) as host_count
            FROM metrics
            GROUP BY collection_date
            ORDER BY collection_date
        )
        SELECT 
            collection_date,
            host_count,
            host_count - LAG(host_count) OVER (ORDER BY collection_date) as net_change
        FROM date_hosts
    """
    ).fetchall()

    print("\nHost Count Over Time:")
    print("-" * 70)
    print(f"{'Date':<15} {'Total Hosts':<15} {'Net Change':<15}")
    print("-" * 70)

    for row in result:
        date, count, change = row
        change_str = f"{change:+d}" if change is not None else "baseline"
        print(f"{date!s:<15} {count:<15} {change_str:<15}")

    # Get host that appeared and disappeared
    result = conn.execute(
        """
        WITH host_dates AS (
            SELECT 
                fqdn,
                hostname,
                MIN(collection_date) as first_seen,
                MAX(collection_date) as last_seen,
                COUNT(DISTINCT collection_date) as appearances
            FROM metrics
            GROUP BY fqdn, hostname
        ),
        total_dates AS (
            SELECT COUNT(DISTINCT collection_date) as total
            FROM metrics
        )
        SELECT 
            h.fqdn,
            h.hostname,
            h.first_seen,
            h.last_seen,
            h.appearances,
            t.total,
            CASE 
                WHEN h.appearances < t.total THEN 'transient'
                ELSE 'persistent'
            END as status
        FROM host_dates h, total_dates t
        WHERE h.appearances < t.total
        ORDER BY h.appearances, h.fqdn
    """
    ).fetchall()

    if result:
        print("\n\nTransient Hosts (not present in all datasets):")
        print("-" * 70)
        print(
            f"{'FQDN':<35} {'Hostname':<12} {'First':<12} {'Last':<12} {'Present':<10}"
        )
        print("-" * 70)

        for row in result:
            fqdn, hostname, first, last, appearances, total, status = row
            print(
                f"{fqdn:<35} {hostname:<12} {first!s:<12} {last!s:<12} {appearances}/{total}"
            )
    else:
        print("\n\nAll hosts are persistent across all collection dates.")

    print("\n" + "=" * 70)


def main():
    """Main execution function"""
    try:
        generate_all_reports()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nPlease run merge_datasets.py first to create the database.")
        return 1
    except Exception as e:
        print(f"❌ Error generating reports: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
