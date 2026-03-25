# Dell iDRAC Administration Scripts

Python scripts for managing Dell servers via iDRAC 9 Redfish API. Provides session management, bulk operations, and automated host list management.

## Features

### 🔌 iDRAC Redfish API Client (`idrac_client.py`)
- **Session Management** - Automatic session creation and cleanup
- **SSL Configuration** - Configurable certificate verification
- **Environment Config** - Credentials from environment variables
- **Context Manager** - Automatic resource cleanup
- **Common Operations** - System info, power state, health status
- **Bulk Testing** - Test connectivity to multiple iDRACs

### 📋 Host File Management (`hostfile.py`)
- **Read/Write** - Manage lists of hosts from text files
- **Auto-Remove** - Remove hosts from list when operations succeed
- **Backup/Restore** - Automatic backup before modifications
- **Gold File Pattern** - Immutable host lists with timestamped working copies
- **Batch Processing** - Process multiple hosts with callbacks
- **Validation** - Check for duplicates, validate format
- **Comments** - Support for comment lines in host files

### 🔄 Workflow Features
- Process lists of servers automatically
- Remove successful hosts from the list
- Retry only failed hosts
- Track progress across multiple runs
- Backup host lists before operations

## Prerequisites

- Python 3.8 or higher
- Dell iDRAC 9 with Redfish API support
- Network access to iDRAC management interfaces
- Valid iDRAC credentials

## Installation

1. **Navigate to project directory:**
   ```bash
   cd idrac-scripts
   ```

2. **Run activation script (creates .venv and installs dependencies):**
   ```bash
   source activate.sh
   ```
   
   This will:
   - Create a local `.venv` virtual environment
   - Install all required Python packages
   - Activate the environment

3. **Configure credentials:**
   ```bash
   cp .env-example .env
   nano .env  # Edit with your iDRAC credentials
   ```
   
   Set your iDRAC username and password:
   ```env
   IDRAC_USERNAME=root
   IDRAC_PASSWORD=your_password_here
   IDRAC_VERIFY_CERT=false
   ```

## Quick Start

### Test iDRAC Connection

```bash
# Test single iDRAC
python idrac_client.py 192.168.1.100

# Test multiple iDRACs
python idrac_client.py 192.168.1.100 192.168.1.101 192.168.1.102
```

### Manage Host Files

```bash
# Create a host file
python hostfile.py create hosts.txt 192.168.1.100 192.168.1.101

# List hosts
python hostfile.py list hosts.txt

# Add a host
python hostfile.py add hosts.txt 192.168.1.102

# Remove a host
python hostfile.py remove hosts.txt 192.168.1.102

# Count hosts
python hostfile.py count hosts.txt

# Backup hostfile
python hostfile.py backup hosts.txt

# Create working copy from gold standard (immutable pattern)
python hostfile.py working-copy hosts-gold.txt --work-dir ./work
```

### Gold File Pattern (Immutable Host Lists)

For production environments where you want to preserve the original host list:

```bash
# Create immutable gold standard file
python hostfile.py create hosts-gold.txt 192.168.1.100 192.168.1.101 192.168.1.102

# Option 1: Use the integrated example script
./example_with_gold_file.py hosts-gold.txt --remove-on-success

# Option 2: Create working copy manually
WORKING=$(python hostfile.py working-copy hosts-gold.txt --work-dir ./work | tail -1)
python example_check_power.py "$WORKING" --remove-on-success --no-backup

# Gold file remains pristine with all original hosts
python hostfile.py list hosts-gold.txt
```

**Benefits:**
- Gold file never modified - always have original list
- Timestamped working copies provide audit trail
- Can run multiple operations in parallel
- Safe for production environments

## Usage Examples

### Example 1: Test Connectivity to Multiple Servers

```python
#!/usr/bin/env python3
from idrac_client import IDracClient
from hostfile import HostFile

# Load hosts from file
hostfile = HostFile('hosts.txt')
hosts = hostfile.read_hosts()

# Test each host
for host in hosts:
    print(f"\nTesting {host}...")
    try:
        client = IDracClient(host)
        if client.test_connection():
            print(f"✓ {host} is accessible")
        else:
            print(f"✗ {host} failed")
    except Exception as e:
        print(f"✗ {host} error: {e}")
```

### Example 2: Process Hosts and Remove on Success

```python
#!/usr/bin/env python3
from idrac_client import IDracClient
from hostfile import HostFile

def check_power_state(host):
    """Check power state and return True if successful."""
    try:
        client = IDracClient(host)
        with client.get_session():
            power_state = client.get_power_state()
            if power_state:
                print(f"{host}: Power state is {power_state}")
                return True
            else:
                print(f"{host}: Failed to get power state")
                return False
    except Exception as e:
        print(f"{host}: Error - {e}")
        return False

# Process all hosts, remove successful ones
hostfile = HostFile('hosts.txt')
success, failed = hostfile.process_hosts(
    callback=check_power_state,
    remove_on_success=True
)

print(f"\nResults: {success} succeeded, {failed} failed")
print(f"Remaining hosts: {hostfile.get_host_count()}")
```

### Example 3: Batch Operation with Context Manager

```python
#!/usr/bin/env python3
from idrac_client import IDracClient

host = "192.168.1.100"
client = IDracClient(host)

# Session is automatically created and cleaned up
with client.get_session():
    # Get system information
    system_info = client.get_system_info()
    if system_info:
        print(f"Model: {system_info.get('Model')}")
        print(f"Serial: {system_info.get('SerialNumber')}")
        print(f"Power: {system_info.get('PowerState')}")
    
    # Get health status
    health, state = client.get_health_status()
    print(f"Health: {health}, State: {state}")
    
    # Make custom API calls
    response = client.get("/Systems/System.Embedded.1/Processors")
    if response.status_code == 200:
        processors = response.json()
        print(f"Processors: {processors['Members@odata.count']}")
```

### Example 4: Set SNMP Community Name with Gold File Pattern

Included script: `set_snmp_community.py`

This production-ready script demonstrates:
- Gold file pattern for audit trail
- Secure credential handling (SNMP community from .env)
- Read-before-write pattern (only update if needed)
- Comprehensive reporting

```bash
# Add SNMP community to .env
echo "SNMP_COMMUNITY=YourSecureCommunity" >> .env

# Create gold file with all iDRACs
python hostfile.py create idrac-gold.txt 192.168.1.100 192.168.1.101 192.168.1.102

# Dry run - check what would be changed
./set_snmp_community.py idrac-gold.txt --dry-run

# Execute - creates working copy, updates only if needed
./set_snmp_community.py idrac-gold.txt

# Output includes detailed report:
# - Already correct (no change needed)
# - Updated successfully 
# - Failed to update
# - Connection/verification failures
```

**Key Features:**
- ✅ Reads current value first - only updates if different
- ✅ Verifies update was successful before marking as done
- ✅ SNMP community never exposed in logs (masked as ***)
- ✅ Gold file remains untouched
- ✅ Timestamped working copies for audit trail
- ✅ Detailed report with categorized results

## Environment Variables

Configure via `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `IDRAC_USERNAME` | iDRAC username | `root` |
| `IDRAC_PASSWORD` | iDRAC password | **Required** |
| `IDRAC_VERIFY_CERT` | Verify SSL certificates | `false` |
| `CERT_PATH` | Path to CA certificate bundle | None |
| `SNMP_COMMUNITY` | SNMP v1/v2c community string | None |

## Host File Format

Host files are simple text files with one hostname or IP per line:

```text
# Production servers
192.168.1.100
192.168.1.101
192.168.1.102

# Development servers
dev-server1.example.com
dev-server2.example.com
```

Features:
- Lines starting with `#` are comments
- Empty lines are ignored
- Whitespace is automatically trimmed
- Supports hostnames and IP addresses

## API Methods

### IDracClient

**Session Management:**
- `create_session()` - Create Redfish session
- `delete_session()` - Delete Redfish session
- `get_session()` - Context manager for automatic cleanup

**HTTP Methods:**
- `get(path)` - GET request
- `post(path, data)` - POST request
- `patch(path, data)` - PATCH request
- `delete(path)` - DELETE request

**Convenience Methods:**
- `get_system_info()` - Get system information
- `get_manager_info()` - Get iDRAC manager info
- `get_power_state()` - Get current power state
- `get_health_status()` - Get health and status
- `test_connection()` - Test connectivity and credentials

### HostFile

**File Operations:**
- `create(hosts)` - Create new host file
- `read_hosts()` - Read hosts from file
- `get_host_count()` - Count hosts in file
- `has_host(host)` - Check if host exists

**Host Management:**
- `add_host(host)` - Add single host
- `remove_host(host)` - Remove single host
- `remove_hosts(hosts)` - Remove multiple hosts
- `clear()` - Clear all hosts

**Batch Processing:**
- `process_hosts(callback, remove_on_success)` - Process with callback

**Backup/Restore:**
- `backup()` - Create backup
- `restore(backup_path)` - Restore from backup
- `list_backups()` - List available backups

**Gold File Pattern:**
- `create_working_copy(gold_file, work_dir, timestamp_format)` - Create timestamped working copy (static method)

## Security Considerations

### Credentials
- **Never commit** `.env` file to version control
- Use strong passwords for iDRAC accounts
- Store credentials securely
- Consider using separate read-only accounts for monitoring scripts

### SSL Certificates
- Set `IDRAC_VERIFY_CERT=true` in production
- Use valid SSL certificates
- Store CA bundle securely
- Self-signed certificates: set `IDRAC_VERIFY_CERT=false` (development only)

### Network Security
- Restrict access to iDRAC management network
- Use VPN or secure tunnel for remote access
- Keep iDRAC firmware updated
- Enable iDRAC security features (2FA, IP filtering)

## Host File Management Patterns

### Pattern 1: Simple Host List (Backup Pattern)

Best for development or when you want a single evolving host list:

```bash
# Create host file
python hostfile.py create hosts.txt server1 server2 server3

# Process hosts (auto-backup before modifications)
python example_check_power.py hosts.txt --remove-on-success

# Successful hosts removed, failures remain for retry
python hostfile.py list hosts.txt
```

**Use when:**
- Working with a single list that evolves
- Quick development/testing
- Manual host management is acceptable

### Pattern 2: Gold File (Immutable Pattern)

Best for production with auditability and repeatability:

```bash
# Create immutable gold file (never modified by scripts)
python hostfile.py create hosts-gold.txt server1 server2 server3

# Each operation creates a timestamped working copy
./example_with_gold_file.py hosts-gold.txt --remove-on-success

# Output:
# ✓ Created working copy: work/hosts-gold_20260325_181800.txt
# Processing 3 host(s)...
# Gold file preserved: hosts-gold.txt (3 hosts)
```

**Use when:**
- Production environments requiring auditability
- Need to preserve original host list
- Running multiple operations in parallel
- Compliance or audit requirements

### Working with Gold Files

#### Creating Working Copies

```bash
# CLI command returns path for scripting
WORKING=$(python hostfile.py working-copy hosts-gold.txt --work-dir ./work | tail -1)
echo "Working with: $WORKING"

# Custom timestamp format
python hostfile.py working-copy hosts-gold.txt \
    --work-dir ./runs \
    --timestamp-format "%Y-%m-%d_%H-%M-%S"
```

#### Python API

```python
from hostfile import HostFile

# Create timestamped working copy
working_path = HostFile.create_working_copy(
    gold_file="hosts-gold.txt",
    work_dir="./work",
    timestamp_format="%Y%m%d_%H%M%S"  # Optional
)

if working_path:
    # Work with copy (auto_backup=False since it's already a copy)
    hf = HostFile(str(working_path), auto_backup=False)
    
    success, fail = hf.process_hosts(
        callback=your_function,
        remove_on_success=True
    )
    
    # Gold file remains untouched!
```

#### Common Gold File Workflows

**Workflow A: Single Operation**
```bash
# Use integrated example (easiest)
./example_with_gold_file.py hosts-gold.txt --remove-on-success
```

**Workflow B: Chain Multiple Operations**
```bash
# Create one working copy, run multiple scripts
WORKING=$(python hostfile.py working-copy hosts-gold.txt --work-dir ./work | tail -1)

./script1_check_power.py "$WORKING" --remove-on-success --no-backup
./script2_update_firmware.py "$WORKING" --remove-on-success --no-backup
./script3_verify_health.py "$WORKING" --remove-on-success --no-backup

# Check final status
python hostfile.py list "$WORKING"
```

**Workflow C: Parallel Operations**
```bash
# Different operations can run simultaneously
./operation1.py hosts-gold.txt --work-dir ./work1 &
./operation2.py hosts-gold.txt --work-dir ./work2 &
wait

# Gold file never conflicts
```

#### Directory Structure with Gold Files

```
idrac-scripts/
├── hosts-gold.txt          # Immutable gold standard (never modified)
├── work/                   # Working copies
│   ├── hosts-gold_20260325_093000.txt
│   ├── hosts-gold_20260325_140530.txt
│   └── hosts-gold_20260325_181800.txt
└── runs/                   # Alternative work directory
    └── hosts-gold_20260325_164500.txt
```

**Best Practices:**
- Never modify gold files manually - treat as read-only
- Use descriptive names: `hosts-gold.txt`, `production-servers-gold.txt`
- Choose dedicated work directories to keep organized
- Clean up old working copies periodically
- Disable `auto_backup` when working with copies (already timestamped)

## Common Workflows

### Workflow 1: Initial Server Inventory

1. Create host file with all servers
2. Run inventory script to collect system information
3. Successful servers are removed from list
4. Re-run on remaining failed servers

### Workflow 2: Firmware Updates

1. Create host file with servers needing updates
2. Run update script
3. Successful updates are removed from list
4. Failed updates remain for retry
5. Backup original host file for reference

### Workflow 3: Health Monitoring

1. Load servers from host file
2. Check health status on each
3. Remove healthy servers from list
4. Alert on remaining problematic servers
5. Re-check failed servers later

## Troubleshooting

### Connection Issues

**Problem:** `Failed to create session`

**Solutions:**
- Verify iDRAC is accessible: `ping <idrac_ip>`
- Check credentials in `.env` file
- Verify iDRAC Redfish API is enabled
- Check firewall rules (port 443)

### SSL Certificate Errors

**Problem:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions:**
- Set `IDRAC_VERIFY_CERT=false` for testing (not recommended for production)
- Install CA certificate and set `CERT_PATH`
- Use valid SSL certificate on iDRAC

### Permission Errors

**Problem:** `Access denied` or `Insufficient privileges`

**Solutions:**
- Verify iDRAC user has required privileges
- Check user account is not locked
- Ensure user has Administrator role for full access

## Dependencies

- **requests** - HTTP library for API calls
- **python-dotenv** - Environment variable management
- **urllib3** - HTTP client (dependency of requests)

## Architecture

```
idrac-scripts/
├── idrac_client.py      # Redfish API client
├── hostfile.py          # Host file management
├── requirements.txt     # Python dependencies
├── activate.sh          # Environment setup
├── .env-example         # Configuration template
├── .gitignore          # Exclude sensitive files
└── README.md           # This file

Future scripts:
├── power_control.py    # Power operations
├── firmware_update.py  # Firmware management
├── inventory.py        # Hardware inventory
└── health_check.py     # Health monitoring
```

## Creating New Scripts

Template for new iDRAC scripts:

```python
#!/usr/bin/env python3
"""
Description of your script.
"""

import sys
from idrac_client import IDracClient
from hostfile import HostFile

def process_host(host: str) -> bool:
    """Process a single host. Return True on success."""
    try:
        client = IDracClient(host)
        with client.get_session():
            # Your operations here
            info = client.get_system_info()
            # ... do something ...
            return True
    except Exception as e:
        print(f"Error on {host}: {e}")
        return False

def main():
    hostfile = HostFile('hosts.txt')
    success, failed = hostfile.process_hosts(
        callback=process_host,
        remove_on_success=True
    )
    print(f"Results: {success} succeeded, {failed} failed")
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
```

## Contributing

To add new functionality:

1. Follow existing patterns in `idrac_client.py` and `hostfile.py`
2. Use environment variables for configuration
3. Implement proper error handling
4. Support batch operations via host files
5. Add comprehensive help text
6. Update this README

## Dell Redfish API Resources

- [Dell iDRAC Redfish API Guide](https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v3.x-series/idrac_3.30.30.30_redfishapiguide/)
- [Redfish Specification](https://www.dmtf.org/standards/redfish)
- [Dell iDRAC 9 Documentation](https://www.dell.com/support/kbdoc/en-us/000177313/idrac9-home)

## License

This project is for Dell server administration purposes.
