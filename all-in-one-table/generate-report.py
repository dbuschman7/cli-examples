#!/usr/bin/env python3
"""
Read parquet file and generate an HTML report with system statistics.
"""

import argparse
from datetime import datetime
from pathlib import Path
import re

import pandas as pd


def generate_html_report(df: pd.DataFrame, output_file: Path):
    """Generate an HTML report from the DataFrame.

    Args:
        df: Pandas DataFrame with system data
        output_file: Path to save the HTML report
    """
    # Calculate statistics
    total_systems = df["system_name"].nunique()
    total_records = len(df)

    # Statistics by system
    system_stats = (
        df.groupby("system_name")
        .agg(
            {
                "cpu_usage": ["mean", "min", "max"],
                "memory_usage": ["mean", "min", "max"],
                "disk_usage": ["mean", "min", "max"],
                "hostname": "count",
            }
        )
        .round(2)
    )

    # Rename columns for clarity
    system_stats.columns = [
        "_".join(col).strip() for col in system_stats.columns.values
    ]
    system_stats = system_stats.rename(columns={"hostname_count": "record_count"})

    # Overall statistics
    overall_stats = df[["cpu_usage", "memory_usage", "disk_usage"]].describe().round(2)

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Data Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #ddd;
            padding-bottom: 8px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
            margin-top: 30px;
            text-align: center;
        }}
        .metric-good {{ color: #4CAF50; font-weight: 600; }}
        .metric-warning {{ color: #FF9800; font-weight: 600; }}
        .metric-critical {{ color: #f44336; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>System Data Report</h1>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Systems</h3>
                <p class="value">{total_systems}</p>
            </div>
            <div class="summary-card">
                <h3>Total Records</h3>
                <p class="value">{total_records}</p>
            </div>
            <div class="summary-card">
                <h3>Avg CPU Usage</h3>
                <p class="value">{df['cpu_usage'].mean():.1f}%</p>
            </div>
            <div class="summary-card">
                <h3>Avg Memory Usage</h3>
                <p class="value">{df['memory_usage'].mean():.1f}%</p>
            </div>
        </div>

        <h2>Statistics by System</h2>
        {system_stats.to_html(classes='data-table', escape=False)}

        <h2>Overall Statistics</h2>
        {overall_stats.to_html(classes='data-table', escape=False)}

        <h2>All System Records</h2>
        {df.to_html(index=False, classes='data-table', escape=False)}

        <div class="timestamp">
            Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)


def extract_date_from_dirname(dirname: str) -> str:
    """Extract date from directory name in format data-YYYY-MM-DD.

    Args:
        dirname: Directory name like 'data-2024-01-12'

    Returns:
        Date string in YYYY-MM-DD format
    """
    match = re.search(r"data-(\d{4}-\d{2}-\d{2})", dirname)
    if match:
        return match.group(1)
    # If no date found, use today's date
    return datetime.now().strftime("%Y-%m-%d")


def main():
    """Main entry point - read parquet and generate HTML report."""
    parser = argparse.ArgumentParser(
        description="Generate HTML report from parquet file"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Data subdirectory (e.g., 'data-2024-01-12' or 'data')",
    )
    args = parser.parse_args()

    # Resolve data directory
    data_dir = Path(__file__).parent / args.data_dir

    if not data_dir.exists():
        print(f"Error: Data directory does not exist: {data_dir}")
        return

    # Extract date from directory name for file naming
    date_str = extract_date_from_dirname(args.data_dir)
    input_file = data_dir / f"system_data_{date_str}.parquet"
    output_file = data_dir / f"system_report_{date_str}.html"

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print(
            f"Please run ingest-to-parquet.py --data-dir {args.data_dir} first to generate the parquet file."
        )
        return

    print(f"Data directory: {data_dir}")
    print(f"Date: {date_str}")
    print(f"Reading data from: {input_file}")
    df = pd.read_parquet(input_file, engine="pyarrow")

    print(f"Loaded {len(df)} records from {df['system_name'].nunique()} systems")

    # Display basic info
    print("\n" + "=" * 50)
    print("DataFrame Info:")
    print("=" * 50)
    print(df.info())

    print("\n" + "=" * 50)
    print("Statistics by System:")
    print("=" * 50)
    print(df.groupby("system_name")[["cpu_usage", "memory_usage", "disk_usage"]].mean())

    # Generate HTML report
    print(f"\nGenerating HTML report...")
    generate_html_report(df, output_file)
    print(f"Report saved to: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.2f} KB")


if __name__ == "__main__":
    main()
