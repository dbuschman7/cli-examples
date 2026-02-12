#!/usr/bin/env python3
"""
Scan all data-* directories for system_data_ prefixed parquet files
and merge them into a DuckDB database with separate hostname and metrics tables.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import glob
from datetime import datetime
import duckdb


def find_data_directories(base_path: str = ".") -> List[Path]:
    """
    Find all directories matching the pattern 'data-*'

    Args:
        base_path: Base directory to search in (default: current directory)

    Returns:
        List of Path objects for matching directories
    """
    base = Path(base_path)
    data_dirs = sorted(base.glob("data-*"))
    return [d for d in data_dirs if d.is_dir()]


def find_parquet_files(directory: Path, prefix: str = "system_data_") -> List[Path]:
    """
    Find all parquet files with the specified prefix in a directory

    Args:
        directory: Directory to search in
        prefix: File name prefix to match (default: 'system_data_')

    Returns:
        List of Path objects for matching parquet files
    """
    pattern = f"{prefix}*.parquet"
    parquet_files = sorted(directory.glob(pattern))
    return parquet_files


def scan_all_data_directories(base_path: str = ".") -> Dict[str, List[Path]]:
    """
    Scan all data-* directories and find system_data_ prefixed parquet files

    Args:
        base_path: Base directory to search in (default: current directory)

    Returns:
        Dictionary mapping directory names to lists of parquet files
    """
    results = {}

    data_dirs = find_data_directories(base_path)

    for data_dir in data_dirs:
        parquet_files = find_parquet_files(data_dir)
        if parquet_files:
            results[str(data_dir)] = parquet_files

    return results


def print_results(results: Dict[str, List[Path]]):
    """
    Print the scan results in a readable format

    Args:
        results: Dictionary of directory to parquet files
    """
    if not results:
        print("No parquet files found in any data-* directories")
        return

    print(f"Found parquet files in {len(results)} data directories:\n")

    total_files = 0
    for directory, files in results.items():
        print(f"📁 {directory}")
        for file in files:
            print(f"   📄 {file.name}")
            total_files += 1
        print()

    print(f"Total: {total_files} parquet file(s)")


def main():
    """Main execution function"""
    print("Scanning for system_data_ prefixed parquet files...\n")

    # Get the script's directory as base path
    script_dir = Path(__file__).parent

    # Scan for parquet files
    results = scan_all_data_directories(script_dir)

    # Print results
    print_results(results)

    # Initialize database
    db_path = script_dir / "database"
    db_path.mkdir(exist_ok=True)

    db_file = db_path / "system_metrics.duckdb"
    print(f"\n{'='*60}")
    print(f"Initializing DuckDB database: {db_file}")
    print(f"{'='*60}\n")

    # Process parquet files and merge into database
    process_parquet_files(results, db_file)

    # Display summary
    display_database_summary(db_file)

    return results


def initialize_database(conn: duckdb.DuckDBPyConnection):
    """
    Initialize the DuckDB database with hostname and metrics tables

    Args:
        conn: DuckDB connection
    """
    print("Creating database schema...")

    # Create hostnames table (static/semi-static info)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS hostnames (
            fqdn VARCHAR PRIMARY KEY,
            hostname VARCHAR,
            ip_address VARCHAR,
            system VARCHAR,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Create metrics table (time-series data)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            fqdn VARCHAR NOT NULL,
            hostname VARCHAR NOT NULL,
            collection_date DATE NOT NULL,
            cpu_usage DOUBLE,
            memory_usage DOUBLE,
            disk_usage DOUBLE,
            network_in DOUBLE,
            network_out DOUBLE,
            process_count INTEGER,
            uptime_hours DOUBLE,
            ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (fqdn, collection_date)
        )
    """
    )

    print("✓ Schema created successfully\n")


def extract_date_from_path(file_path: Path) -> Optional[str]:
    """
    Extract date from parquet file path (e.g., 'data-2025-12-19/system_data_2025-12-19.parquet')

    Args:
        file_path: Path to the parquet file

    Returns:
        Date string in YYYY-MM-DD format or None
    """
    import re

    # Try to extract from filename first
    match = re.search(r"(\d{4}-\d{2}-\d{2})", file_path.name)
    if match:
        return match.group(1)

    # Try to extract from parent directory
    match = re.search(r"data-(\d{4}-\d{2}-\d{2})", str(file_path.parent))
    if match:
        return match.group(1)

    return None


def parse_fqdn(fqdn: str) -> str:
    """
    Extract system name from FQDN (e.g., 'srv01.alpha.example.com' -> 'alpha')

    Args:
        fqdn: Fully qualified domain name

    Returns:
        System name or empty string
    """
    if not fqdn:
        return ""

    parts = fqdn.split(".")
    if len(parts) >= 2:
        return parts[1]
    return ""


def merge_hostnames(conn: duckdb.DuckDBPyConnection, parquet_file: Path):
    """
    Merge hostname information from parquet file into hostnames table

    Args:
        conn: DuckDB connection
        parquet_file: Path to parquet file
    """
    # Read parquet file and extract hostname info
    temp_table = f"temp_hosts_{parquet_file.stem.replace('-', '_')}"

    conn.execute(
        f"""
        CREATE TEMP TABLE {temp_table} AS
        SELECT DISTINCT
            fqdn,
            hostname,
            ip_address,
            COALESCE(fqdn_system, system_name, '') AS system
        FROM read_parquet('{parquet_file}')
        WHERE fqdn IS NOT NULL
    """
    )

    # MERGE INTO hostnames table
    conn.execute(
        f"""
        MERGE INTO hostnames AS target
        USING {temp_table} AS source
        ON target.fqdn = source.fqdn
        WHEN MATCHED THEN
            UPDATE SET
                hostname = source.hostname,
                ip_address = source.ip_address,
                system = source.system,
                last_updated = CURRENT_TIMESTAMP
        WHEN NOT MATCHED THEN
            INSERT (fqdn, hostname, ip_address, system)
            VALUES (source.fqdn, source.hostname, source.ip_address, source.system)
    """
    )

    # Clean up temp table
    conn.execute(f"DROP TABLE {temp_table}")


def merge_metrics(
    conn: duckdb.DuckDBPyConnection, parquet_file: Path, collection_date: str
):
    """
    Merge metrics information from parquet file into metrics table

    Args:
        conn: DuckDB connection
        parquet_file: Path to parquet file
        collection_date: Date when metrics were collected (YYYY-MM-DD format)
    """
    temp_table = f"temp_metrics_{parquet_file.stem.replace('-', '_')}"

    # Read parquet file and extract metrics
    conn.execute(
        f"""
        CREATE TEMP TABLE {temp_table} AS
        SELECT
            fqdn,
            hostname,
            CAST('{collection_date}' AS DATE) AS collection_date,
            cpu_usage,
            memory_usage,
            disk_usage,
            network_in,
            network_out,
            process_count,
            uptime_hours
        FROM read_parquet('{parquet_file}')
        WHERE fqdn IS NOT NULL
    """
    )

    # MERGE INTO metrics table
    conn.execute(
        f"""
        MERGE INTO metrics AS target
        USING {temp_table} AS source
        ON target.fqdn = source.fqdn 
           AND target.collection_date = source.collection_date
        WHEN MATCHED THEN
            UPDATE SET
                hostname = source.hostname,
                cpu_usage = source.cpu_usage,
                memory_usage = source.memory_usage,
                disk_usage = source.disk_usage,
                network_in = source.network_in,
                network_out = source.network_out,
                process_count = source.process_count,
                uptime_hours = source.uptime_hours,
                ingestion_timestamp = CURRENT_TIMESTAMP
        WHEN NOT MATCHED THEN
            INSERT (fqdn, hostname, collection_date, cpu_usage, memory_usage, disk_usage,
                    network_in, network_out, process_count, uptime_hours)
            VALUES (source.fqdn, source.hostname, source.collection_date, source.cpu_usage,
                    source.memory_usage, source.disk_usage, source.network_in,
                    source.network_out, source.process_count, source.uptime_hours)
    """
    )

    # Clean up temp table
    conn.execute(f"DROP TABLE {temp_table}")


def process_parquet_files(results: Dict[str, List[Path]], db_file: Path):
    """
    Process all parquet files and merge data into DuckDB database

    Args:
        results: Dictionary mapping directories to parquet files
        db_file: Path to DuckDB database file
    """
    if not results:
        print("No parquet files to process")
        return

    # Connect to database
    conn = duckdb.connect(str(db_file))

    try:
        # Initialize schema
        initialize_database(conn)

        # Process each parquet file
        total_files = sum(len(files) for files in results.values())
        processed = 0

        print(f"Processing {total_files} parquet file(s)...\n")

        for directory, files in sorted(results.items()):
            for parquet_file in files:
                processed += 1
                print(f"[{processed}/{total_files}] Processing: {parquet_file.name}")

                # Extract collection date from file path
                collection_date = extract_date_from_path(parquet_file)
                if not collection_date:
                    print(f"  ⚠️  Warning: Could not extract date from {parquet_file}")
                    continue

                print(f"  📅 Collection date: {collection_date}")

                # Merge hostname info
                print(f"  🔄 Merging hostname data...")
                merge_hostnames(conn, parquet_file)

                # Merge metrics data
                print(f"  🔄 Merging metrics data...")
                merge_metrics(conn, parquet_file, collection_date)

                print(f"  ✓ Completed\n")

        print(f"{'='*60}")
        print(f"✓ Successfully processed {processed} parquet file(s)")
        print(f"{'='*60}\n")

    finally:
        conn.close()


def display_database_summary(db_file: Path):
    """
    Display summary statistics from the database

    Args:
        db_file: Path to DuckDB database file
    """
    conn = duckdb.connect(str(db_file))

    try:
        print("Database Summary:")
        print("-" * 60)

        # Hostnames summary
        result = conn.execute("SELECT COUNT(*) FROM hostnames").fetchone()
        hostname_count = result[0] if result else 0
        print(f"📊 Total unique hostnames: {hostname_count}")

        # Metrics summary
        result = conn.execute("SELECT COUNT(*) FROM metrics").fetchone()
        metrics_count = result[0] if result else 0
        print(f"📊 Total metrics records: {metrics_count}")

        # Date range
        result = conn.execute(
            """
            SELECT 
                MIN(collection_date) as first_date,
                MAX(collection_date) as last_date,
                COUNT(DISTINCT collection_date) as unique_dates
            FROM metrics
        """
        ).fetchone()

        if result and result[0]:
            print(f"📅 Date range: {result[0]} to {result[1]}")
            print(f"📅 Unique collection dates: {result[2]}")

        # Systems summary
        result = conn.execute(
            """
            SELECT system, COUNT(*) as count
            FROM hostnames
            WHERE system != ''
            GROUP BY system
            ORDER BY count DESC
        """
        ).fetchall()

        if result:
            print(f"\n🖥️  Hosts by system:")
            for system, count in result:
                print(f"   {system}: {count} host(s)")

        print(f"\n{'='*60}")
        print(f"Database location: {db_file}")
        print(f"{'='*60}")

    finally:
        conn.close()


def main():
    """Main execution function"""
    print("Scanning for system_data_ prefixed parquet files...\n")

    # Get the script's directory as base path
    script_dir = Path(__file__).parent

    # Scan for parquet files
    results = scan_all_data_directories(script_dir)

    # Print results
    print_results(results)

    # Initialize database
    db_path = script_dir / "database"
    db_path.mkdir(exist_ok=True)

    db_file = db_path / "system_metrics.duckdb"
    print(f"\n{'='*60}")
    print(f"Initializing DuckDB database: {db_file}")
    print(f"{'='*60}\n")

    # Process parquet files and merge into database
    process_parquet_files(results, db_file)

    # Display summary
    display_database_summary(db_file)

    return results


if __name__ == "__main__":
    main()
