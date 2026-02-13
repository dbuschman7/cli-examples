# Nessus Security Center API Client

Python script to fetch scan results from Nessus Tenable Security Center using username/password authentication.

## Features

- ✅ Username/password authentication (no API keys needed)
- ✅ Fetch scan details and results by scan ID
- ✅ Support for multiple scans in one request
- ✅ Custom SSL certificate support
- ✅ Optional SSL verification bypass
- ✅ Export results to JSON file
- ✅ Proper session management with automatic logout

## Requirements

```bash
pip install requests
```

## Usage

### Basic Example

```bash
python fetch_scans.py \
  --url https://sc.example.com \
  --username admin \
  --password yourpassword \
  --scans 123
```

### Fetch Multiple Scans

```bash
python fetch_scans.py \
  --url https://sc.example.com \
  --username admin \
  --password yourpassword \
  --scans 123,456,789
```

### Use Custom SSL Certificate

```bash
python fetch_scans.py \
  --url https://sc.example.com \
  --username admin \
  --password yourpassword \
  --scans 123 \
  --cert /path/to/ca-cert.pem
```

### Disable SSL Verification (Not Recommended)

```bash
python fetch_scans.py \
  --url https://sc.example.com \
  --username admin \
  --password yourpassword \
  --scans 123 \
  --no-verify
```

### Save Results to File

```bash
python fetch_scans.py \
  --url https://sc.example.com \
  --username admin \
  --password yourpassword \
  --scans 123,456 \
  --output scan_results.json
```

### Fetch Scan Results (Instead of Scan Details)

```bash
python fetch_scans.py \
  --url https://sc.example.com \
  --username admin \
  --password yourpassword \
  --scans 123 \
  --results-only
```

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--url` | `-u` | Security Center base URL (required) |
| `--username` | `-U` | Username for authentication (required) |
| `--password` | `-P` | Password for authentication (required) |
| `--scans` | `-s` | Comma-separated scan IDs (required) |
| `--output` | `-o` | Output file path for JSON results |
| `--cert` | | Path to custom CA certificate file |
| `--no-verify` | | Disable SSL certificate verification |
| `--results-only` | | Fetch scan results instead of scan details |

## API Endpoints Used

- `POST /rest/token` - Login with username/password
- `GET /rest/scan/{id}` - Get scan details
- `GET /rest/scanResult/{id}` - Get scan results
- `DELETE /rest/token` - Logout

## Example Output

```
Fetching data for 2 scan(s): [123, 456]

Logging in to https://sc.example.com...
✓ Successfully logged in as admin

Fetching scan 123...
Fetching scan 456...

======================================================================
Successfully fetched data for 2 scan(s)
======================================================================

Scan 123: ✓ Weekly Network Scan (Status: Completed)
Scan 456: ✓ Monthly Vulnerability Assessment (Status: Running)

✓ Results saved to scan_results.json
✓ Logged out successfully
```

## Error Handling

The script includes comprehensive error handling for:
- Network connectivity issues
- Authentication failures
- Invalid scan IDs
- SSL certificate problems
- API errors

## Security Notes

- Credentials are passed via command line (consider using environment variables in production)
- Always use SSL verification in production environments
- The script automatically logs out after fetching data
- Session tokens are properly managed and invalidated

## Programmatic Usage

You can also use the `NessusSecurityCenterClient` class in your own scripts:

```python
from fetch_scans import NessusSecurityCenterClient

client = NessusSecurityCenterClient(
    base_url="https://sc.example.com",
    username="admin",
    password="password",
    cert_file="/path/to/cert.pem"  # optional
)

try:
    # Login
    client.login()
    
    # Fetch single scan
    scan = client.get_scan(123)
    print(f"Scan name: {scan['name']}")
    
    # Fetch scan results
    results = client.get_scan_results(123)
    
    # Fetch multiple scans
    scans = client.get_multiple_scans([123, 456, 789])
    
finally:
    # Always logout
    client.logout()
```

## Troubleshooting

### SSL Certificate Errors

If you encounter SSL certificate errors:
1. Use `--cert` to specify a custom CA certificate
2. As a last resort, use `--no-verify` (not recommended for production)

### Authentication Errors

- Verify your username and password are correct
- Check that your user has appropriate permissions in Security Center
- Ensure the Security Center URL is correct (including https://)

### Scan Not Found

- Verify the scan ID exists in Security Center
- Check that your user has permission to view the scan
