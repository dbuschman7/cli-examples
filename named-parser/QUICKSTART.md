# Quick Start Guide

## Setup (One-time)

```bash
# Navigate to the project directory
cd named-parser

# Create and activate virtual environment
python3 -m venv ../.venv
source activate.sh

# Install dependencies
pip install -r requirements.txt
```

## Test with Example Files

```bash
# Run the example analysis script
python example_usage.py
```

This will parse the three example zone files and show:
- All base hostnames with IPs (A records)
- All aliases (CNAME records) 
- All reverse lookups (PTR records)
- Forward/reverse DNS consistency check
- IP address distribution

## Parse Your Own Zone Files

```bash
# Single zone file
python zone_parser.py /path/to/your/zone.file

# Multiple zone files
python zone_parser.py forward.zone reverse.zone -o output.parquet
```

## Analyze Results in Python

```python
import pandas as pd

# Load the parquet file
df = pd.read_parquet('dns_records.parquet')

# Show all A records (base hostnames)
print(df[df['type'] == 'A'][['hostname', 'ip']])

# Show all CNAMEs (aliases)
print(df[df['is_cname'] == True][['hostname', 'canonical_name']])

# Find hosts missing reverse DNS
forwards = set(df[df['type'] == 'A']['hostname'])
reverses = set(df[df['type'] == 'PTR']['hostname'])
missing = forwards - reverses
print(f"Missing reverse DNS: {missing}")
```

## Key Concepts

### Base Hostname vs CNAME

**Base hostname** = Has an A record (maps directly to an IP)
```
web    IN  A      192.168.1.30
```

**CNAME (alias)** = Points to another hostname
```
www    IN  CNAME  web.example.com.
```

### Reverse DNS (PTR)

PTR records should point to **base hostnames**, not CNAMEs:

✅ **Correct:**
```
Forward:  web.example.com.      A       192.168.1.30
Reverse:  30.1.168.192...arpa.  PTR     web.example.com.
```

❌ **Wrong:**
```
Forward:  www.example.com.      CNAME   web.example.com.
Reverse:  30.1.168.192...arpa.  PTR     www.example.com.  # WRONG!
```

## Output Schema

| Column | Description |
|--------|-------------|
| `hostname` | The hostname or FQDN |
| `ip` | IP address (for A/PTR records) |
| `type` | Record type (A, CNAME, PTR, MX, NS, etc.) |
| `is_cname` | True if this is a CNAME/alias |
| `canonical_name` | For CNAMEs, the target hostname |
| `value` | Raw record value |
| `ttl` | Time To Live |
| `priority` | Priority (for MX records) |
