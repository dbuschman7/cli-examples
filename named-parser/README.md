# DNS Zone File Parser

A Python utility for parsing BIND-style DNS zone files (both forward and reverse zones) and extracting structured data into a pandas DataFrame and Parquet format.

## Features

- **Parse Forward Zones**: Extract A records, CNAME records, NS records, MX records, etc.
- **Parse Reverse Zones**: Extract PTR records for reverse DNS lookups
- **Handle Comments**: Properly ignores comments (lines starting with `;`)
- **Support Directives**: Handles `$ORIGIN` and `$TTL` directives
- **CNAME Detection**: Identifies which hostnames are CNAMEs (aliases) vs base hostnames
- **Structured Output**: Creates pandas DataFrame with clear columns
- **Parquet Export**: Saves data to efficient Parquet format for further analysis

## Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv ../.venv
source activate.sh
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Parse one or more zone files:

```bash
python zone_parser.py example-forward.zone example-reverse.zone
```

This will create `dns_records.parquet` with all parsed records.

### Specify Output File

```bash
python zone_parser.py example-forward.zone -o output.parquet
```

### Parse Multiple Zones

```bash
python zone_parser.py forward.zone reverse-192.zone reverse-10.zone -o all_dns.parquet
```

## Output DataFrame Schema

The parsed data includes these columns:

| Column | Description |
|--------|-------------|
| `hostname` | The hostname or record name |
| `ip` | IP address (for A and PTR records) |
| `type` | Record type (A, CNAME, PTR, MX, NS, etc.) |
| `is_cname` | Boolean - True if this is a CNAME record |
| `canonical_name` | For CNAMEs, the target/canonical hostname |
| `value` | The record value (IP, hostname, etc.) |
| `ttl` | Time To Live value |
| `priority` | Priority (for MX records) |

## Understanding Forward vs Reverse Zones

### Forward Zone (hostname → IP)

Forward zones map hostnames to IP addresses:

```
; Base hostname with A record
web             IN      A       192.168.1.30

; Alias (CNAME) pointing to base hostname
www             IN      CNAME   web.example.com.
```

**Key Points:**
- `web.example.com` is the **base hostname** (has an A record)
- `www.example.com` is a **CNAME/alias** (points to web.example.com)

### Reverse Zone (IP → hostname)

Reverse zones map IP addresses back to hostnames using PTR records:

```
; PTR record points to BASE hostname, not CNAME
30              IN      PTR     web.example.com.
```

**Important:** PTR records should point to the **base hostname**, not CNAMEs:
- ✅ Correct: `192.168.1.30 → web.example.com` (base hostname)
- ❌ Wrong: `192.168.1.30 → www.example.com` (CNAME)

## Example Files

The repository includes example zone files:

- `example-forward.zone` - Forward zone for example.com
- `example-reverse.zone` - Reverse zone for 192.168.1.0/24

These demonstrate:
- A records (base hostnames)
- CNAME records (aliases)
- PTR records (reverse lookups)
- Comments and directives
- MX records, NS records

## Analyzing the Results

After parsing, you can load the Parquet file with pandas:

```python
import pandas as pd

df = pd.read_parquet('dns_records.parquet')

# Show all A records
print(df[df['type'] == 'A'])

# Show all CNAMEs
print(df[df['is_cname'] == True])

# Show which hosts have both forward and reverse DNS
forwards = set(df[df['type'] == 'A']['hostname'])
reverses = set(df[df['type'] == 'PTR']['hostname'])
print("Hosts with both forward and reverse:", forwards & reverses)
```

## Use Cases

- **DNS Audit**: Verify all hosts have proper forward and reverse DNS
- **CNAME Analysis**: Identify aliases vs canonical hostnames
- **IP Inventory**: Extract all IP addresses and hostnames
- **Zone Validation**: Check for inconsistencies between forward/reverse zones
- **Documentation**: Generate tables of DNS records

## Dependencies

- `pyparsing >= 3.1.0` - Grammar-based text parsing
- `pandas >= 2.0.0` - Data manipulation and analysis
- `pyarrow >= 14.0.0` - Parquet file format support

## Technical Details

### Parser Implementation

The parser uses `pyparsing` to define a formal grammar for DNS zone file syntax:

1. **Tokenization**: Identifies domain names, IP addresses, record types
2. **Grammar Rules**: Defines patterns for A, CNAME, PTR, MX, NS records
3. **Directives**: Handles `$ORIGIN`, `$TTL`, and SOA records
4. **Comments**: Strips comments before parsing
5. **Error Handling**: Gracefully skips unparseable lines

### Why pyparsing?

- More robust than regex for complex syntax
- Self-documenting grammar
- Better error messages
- Handles nested structures (like SOA records)

## Limitations

- SOA records are detected but not fully parsed (implementation can be extended)
- IPv6 AAAA records are recognized (can be enhanced if needed)
- $INCLUDE directives are not currently supported
- Some exotic record types may not be parsed

## Contributing

To extend the parser:

1. Add new record type patterns in `_setup_grammar()`
2. Update `_extract_record()` to handle new fields
3. Update `build_dataframe()` to include new columns
4. Test with sample zone files

## License

This project is for educational and operational use.
