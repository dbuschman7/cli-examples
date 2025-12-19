#!/usr/bin/env python3
"""
Ingest raw CSV data from multiple systems into a unified pandas DataFrame.
Uses dataclasses to represent system data with metadata.
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd


@dataclass
class SystemRecord:
    """Represents a single record from a system CSV file."""
    hostname: str
    fqdn: str
    ip_address: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_in: float
    network_out: float
    process_count: int
    uptime_hours: int


@dataclass
class SystemData:
    """Container for system data with metadata."""
    system_name: str
    date_generated: datetime
    records: List[SystemRecord] = field(default_factory=list)

    @classmethod
    def from_csv(cls, filepath: Path, system_name: str) -> "SystemData":
        """Load system data from a CSV file."""
        records = []
        with open(filepath, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = SystemRecord(
                    hostname=row["hostname"],
                    fqdn=row["fqdn"],
                    ip_address=row["ip_address"],
                    cpu_usage=float(row["cpu_usage"]),
                    memory_usage=float(row["memory_usage"]),
                    disk_usage=float(row["disk_usage"]),
                    network_in=float(row["network_in"]),
                    network_out=float(row["network_out"]),
                    process_count=int(row["process_count"]),
                    uptime_hours=int(row["uptime_hours"]),
                )
                records.append(record)

        return cls(
            system_name=system_name,
            date_generated=datetime.now(),
            records=records,
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Convert records to a pandas DataFrame with system_name column."""
        data = []
        for record in self.records:
            row = {
                "system_name": self.system_name,
                "date_generated": self.date_generated,
                "hostname": record.hostname,
                "fqdn": record.fqdn,
                "ip_address": record.ip_address,
                "cpu_usage": record.cpu_usage,
                "memory_usage": record.memory_usage,
                "disk_usage": record.disk_usage,
                "network_in": record.network_in,
                "network_out": record.network_out,
                "process_count": record.process_count,
                "uptime_hours": record.uptime_hours,
            }
            data.append(row)
        return pd.DataFrame(data)


def load_all_systems(data_dir: Path) -> tuple[List[SystemData], pd.DataFrame]:
    """
    Load all CSV files from the data directory.
    
    Returns:
        A tuple containing:
        - List of SystemData objects (one per file)
        - Combined pandas DataFrame with all records
    """
    csv_files = {
        "system_alpha.csv": "Alpha",
        "system_beta.csv": "Beta",
        "system_gamma.csv": "Gamma",
    }

    # Store SystemData objects in an array
    system_data_array: List[SystemData] = []

    for filename, system_name in csv_files.items():
        filepath = data_dir / filename
        if filepath.exists():
            system_data = SystemData.from_csv(filepath, system_name)
            system_data_array.append(system_data)
            print(f"Loaded {len(system_data.records)} records from {system_name}")

    # Combine all data into a single DataFrame
    dataframes = [sd.to_dataframe() for sd in system_data_array]
    combined_df = pd.concat(dataframes, ignore_index=True)

    return system_data_array, combined_df


def main():
    """Main entry point."""
    data_dir = Path(__file__).parent / "data"

    print("Loading system data...")
    print("-" * 50)

    system_data_array, combined_df = load_all_systems(data_dir)

    print("-" * 50)
    print(f"\nTotal systems loaded: {len(system_data_array)}")
    print(f"Total records: {len(combined_df)}")

    print("\n" + "=" * 50)
    print("System Data Array Contents:")
    print("=" * 50)
    for sd in system_data_array:
        print(f"\nSystem: {sd.system_name}")
        print(f"  Date Generated: {sd.date_generated}")
        print(f"  Record Count: {len(sd.records)}")

    print("\n" + "=" * 50)
    print("Combined DataFrame:")
    print("=" * 50)
    print(combined_df.to_string())

    print("\n" + "=" * 50)
    print("DataFrame Info:")
    print("=" * 50)
    print(combined_df.info())

    print("\n" + "=" * 50)
    print("Statistics by System:")
    print("=" * 50)
    print(combined_df.groupby("system_name")[["cpu_usage", "memory_usage", "disk_usage"]].mean())


if __name__ == "__main__":
    main()
