# All-in-One Table Data Ingestion

A Python script to ingest raw CSV and XLSX data from multiple systems into a unified pandas DataFrame.

## Features

- **Multi-format support**: Loads both CSV and XLSX files
- **Dataclass-based**: Uses Python dataclasses for structured data representation
- **Unified output**: Combines all data into a single pandas DataFrame
- **Configurable**: Easy to add new data sources via `FileConfig`

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas openpyxl
```

## Usage

```bash
source .venv/bin/activate
python3 ingest-raw-data.py
```

## Data Files

The script loads data from the `data/` directory:

| File | System Name | Type | Sheet Name |
|------|-------------|------|------------|
| `system_alpha.csv` | Alpha | CSV | - |
| `system_beta.csv` | Beta | CSV | - |
| `system_gamma.csv` | Gamma | CSV | - |
| `system_delta.xlsx` | Delta | XLSX | SystemData |
| `system_epsilon.xlsx` | Epsilon | XLSX | SystemData |

## Data Schema

Each record contains:

| Field | Type | Description |
|-------|------|-------------|
| `hostname` | str | Server hostname |
| `fqdn` | str | Fully qualified domain name |
| `ip_address` | str | IP address |
| `cpu_usage` | float | CPU usage percentage |
| `memory_usage` | float | Memory usage percentage |
| `disk_usage` | float | Disk usage percentage |
| `network_in` | float | Network input (bytes) |
| `network_out` | float | Network output (bytes) |
| `process_count` | int | Number of running processes |
| `uptime_hours` | int | System uptime in hours |

## Adding New Data Sources

To add a new data source, add a `FileConfig` entry in the `load_all_systems()` function:

```python
file_configs = [
    # ... existing configs ...
    FileConfig("new_system.csv", "NewSystem", FileType.CSV),
    FileConfig("another_system.xlsx", "Another", FileType.XLSX, sheet_name="Data"),
]
```

## Output

The script outputs:
- Loading progress for each file
- Summary of loaded systems and record counts
- Combined DataFrame contents
- DataFrame info (columns, types, memory usage)
- Statistics grouped by system (mean CPU, memory, disk usage)
