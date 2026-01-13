#!/usr/bin/env python3
"""
Generate a summary report across multiple months of system data.
Reads parquet files from date-based directories and creates a pivot table
showing which system/hostname combinations existed in each time period.
"""

import argparse
from datetime import datetime
from pathlib import Path
import re
from typing import List, Tuple

import pandas as pd


def extract_date_from_dirname(dirname: str) -> str:
    """Extract date from directory name in format data-YYYY-MM-DD.

    Args:
        dirname: Directory name like 'data-2024-01-12'

    Returns:
        Date string in YYYY-MM-DD format or empty string if no match
    """
    match = re.search(r"data-(\d{4}-\d{2}-\d{2})", dirname)
    if match:
        return match.group(1)
    return ""


def find_data_directories(base_dir: Path, num_months: int) -> List[Tuple[str, Path]]:
    """Find all data directories and return the most recent n months.

    Args:
        base_dir: Base directory containing data-YYYY-MM-DD subdirectories
        num_months: Number of most recent months to include

    Returns:
        List of tuples (date_string, directory_path) sorted by date ascending
    """
    data_dirs = []

    # Find all directories matching the pattern
    for item in base_dir.iterdir():
        if item.is_dir() and item.name.startswith("data-"):
            date_str = extract_date_from_dirname(item.name)
            if date_str:
                data_dirs.append((date_str, item))

    # Sort by date
    data_dirs.sort(key=lambda x: x[0])

    # Take the last n months
    if num_months > 0:
        data_dirs = data_dirs[-num_months:]

    return data_dirs


def load_parquet_files(data_dirs: List[Tuple[str, Path]]) -> dict[str, pd.DataFrame]:
    """Load parquet files from each data directory.

    Args:
        data_dirs: List of (date_string, directory_path) tuples

    Returns:
        Dictionary mapping date_string to DataFrame
    """
    datasets = {}

    for date_str, dir_path in data_dirs:
        parquet_file = dir_path / f"system_data_{date_str}.parquet"

        if parquet_file.exists():
            print(f"Loading: {parquet_file}")
            df = pd.read_parquet(parquet_file, engine="pyarrow")
            datasets[date_str] = df
            print(f"  Loaded {len(df)} records")
        else:
            print(f"Warning: Parquet file not found: {parquet_file}")

    return datasets


def create_summary_pivot(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Create a pivot table showing system/hostname presence across dates.

    Args:
        datasets: Dictionary mapping date_string to DataFrame

    Returns:
        DataFrame with system_name, hostname as index and dates as columns
        Values are counts of records for that combination on that date
    """
    # Collect all system/hostname combinations from all datasets
    all_combinations = set()
    date_counts = {}

    for date_str, df in datasets.items():
        # Group by system_name and hostname, count occurrences
        grouped = df.groupby(["system_name", "hostname"]).size()
        date_counts[date_str] = grouped

        # Add all combinations from this dataset
        all_combinations.update(grouped.index.tolist())

    # Convert to sorted list for consistent ordering
    all_combinations = sorted(list(all_combinations))

    # Create the pivot table
    summary_data = []
    for system_name, hostname in all_combinations:
        row = {
            "system_name": system_name,
            "hostname": hostname,
        }

        # Add count for each date
        for date_str in sorted(datasets.keys()):
            if date_str in date_counts:
                count = date_counts[date_str].get((system_name, hostname), 0)
            else:
                count = 0
            row[f"count_{date_str}"] = count

        summary_data.append(row)

    return pd.DataFrame(summary_data)


def main():
    """Main entry point - generate summary report across multiple months."""
    parser = argparse.ArgumentParser(
        description="Generate summary report across multiple months of system data"
    )
    parser.add_argument(
        "--months",
        type=int,
        default=3,
        help="Number of most recent months to include (default: 3)",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    summaries_dir = base_dir / "summaries"

    # Create summaries directory if it doesn't exist
    summaries_dir.mkdir(exist_ok=True)

    print(f"Searching for data directories...")
    print(f"Including last {args.months} months")
    print("-" * 50)

    # Find data directories
    data_dirs = find_data_directories(base_dir, args.months)

    if not data_dirs:
        print("Error: No data directories found matching pattern 'data-YYYY-MM-DD'")
        return

    print(f"\nFound {len(data_dirs)} data directories:")
    for date_str, dir_path in data_dirs:
        print(f"  {date_str}: {dir_path.name}")

    # Load parquet files
    print("\n" + "-" * 50)
    print("Loading parquet files...")
    print("-" * 50)
    datasets = load_parquet_files(data_dirs)

    if not datasets:
        print("Error: No parquet files could be loaded")
        return

    # Create summary pivot table
    print("\n" + "-" * 50)
    print("Creating summary pivot table...")
    print("-" * 50)
    summary_df = create_summary_pivot(datasets)

    # Generate output filenames
    first_date = min(datasets.keys())
    last_date = max(datasets.keys())
    base_filename = f"system_summary_{first_date}_{last_date}"
    output_parquet = summaries_dir / f"{base_filename}.parquet"
    output_excel = summaries_dir / f"{base_filename}.xlsx"

    # Save to parquet
    summary_df.to_parquet(
        output_parquet, engine="pyarrow", compression="snappy", index=False
    )

    # Save to Excel
    summary_df.to_excel(output_excel, index=False, engine="openpyxl")

    print(f"\nSummary Statistics:")
    print(f"  Total unique system/hostname combinations: {len(summary_df)}")
    print(f"  Date range: {first_date} to {last_date}")
    print(f"  Number of date columns: {len(datasets)}")

    print(f"\nSummary Preview:")
    print(summary_df.head(10).to_string())

    print(f"\n" + "-" * 50)
    print(f"Summary saved to:")
    print(f"  Parquet: {output_parquet}")
    print(f"  Parquet size: {output_parquet.stat().st_size / 1024:.2f} KB")
    print(f"  Excel: {output_excel}")
    print(f"  Excel size: {output_excel.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    main()
