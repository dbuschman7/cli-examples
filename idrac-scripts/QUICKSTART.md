# Quick Start Guide - Dell iDRAC Scripts

## 5-Minute Setup

### 1. Activate Environment

```bash
cd idrac-scripts
source activate.sh
```

This automatically:
- Creates `.venv` virtual environment (if needed)
- Installs Python dependencies
- Activates the environment

### 2. Configure Credentials

```bash
cp .env-example .env
nano .env
```

Update with your credentials:
```env
IDRAC_USERNAME=root
IDRAC_PASSWORD=your_actual_password
IDRAC_VERIFY_CERT=false
```

### 3. Test Connection

```bash
# Test single iDRAC
python idrac_client.py 192.168.1.100

# Test multiple iDRACs
python idrac_client.py 192.168.1.100 192.168.1.101
```

Expected output:
```
Testing: 192.168.1.100
============================================================
✓ Connected to iDRAC: 192.168.1.100
  Manufacturer: Dell Inc.
  Model: PowerEdge R640
  Serial: ABC1234
  Power State: On
```

## Common Tasks

### Create and Manage Host Files

```bash
# Create host file with servers
python hostfile.py create hosts.txt 192.168.1.100 192.168.1.101 192.168.1.102

# View hosts
python hostfile.py list hosts.txt

# Add more hosts
python hostfile.py add hosts.txt 192.168.1.103

# Remove a host
python hostfile.py remove hosts.txt 192.168.1.103

# Count hosts
python hostfile.py count hosts.txt

# Create backup before operations
python hostfile.py backup hosts.txt
```

### Process Multiple Servers

Create a simple script to process all hosts:

```python
#!/usr/bin/env python3
from idrac_client import IDracClient
from hostfile import HostFile

def check_server(host):
    """Check server status."""
    try:
        client = IDracClient(host)
        with client.get_session():
            info = client.get_system_info()
            power = info.get('PowerState')
            print(f"✓ {host}: {power}")
            return True
    except Exception as e:
        print(f"✗ {host}: {e}")
        return False

# Process all hosts, remove successful ones
hostfile = HostFile('hosts.txt')
success, failed = hostfile.process_hosts(
    callback=check_server,
    remove_on_success=True
)

print(f"\n{success} succeeded, {failed} failed")
print(f"{hostfile.get_host_count()} hosts remaining")
```

Save as `check_servers.py` and run:
```bash
python check_servers.py
```

### Advanced: Gold File Pattern

For production environments, use the **gold file pattern** where the original host list remains immutable:

```bash
# 1. Create immutable gold standard file
python hostfile.py create hosts-gold.txt 192.168.1.100 192.168.1.101 192.168.1.102

# 2. Use the integrated example - creates timestamped working copy automatically
./example_with_gold_file.py hosts-gold.txt --remove-on-success
```

**What happens:**
- Creates timestamped copy: `work/hosts-gold_20260325_181800.txt`
- Operations modify the working copy only
- Gold file remains pristine with all original hosts
- Each run creates a new timestamped copy (audit trail)

**Manual control:**
```bash
# Create working copy yourself
WORKING=$(python hostfile.py working-copy hosts-gold.txt --work-dir ./work | tail -1)

# Use it with any script
python example_check_power.py "$WORKING" --remove-on-success --no-backup

# Gold file still has all original hosts
python hostfile.py list hosts-gold.txt  # 3 hosts
python hostfile.py list "$WORKING"      # 1 host (if 2 succeeded)
```

**Chain multiple operations:**
```bash
WORKING=$(python hostfile.py working-copy hosts-gold.txt --work-dir ./work | tail -1)

# Run multiple scripts on same working copy
./check_power.py "$WORKING" --remove-on-success --no-backup
./update_firmware.py "$WORKING" --remove-on-success --no-backup
./verify_health.py "$WORKING" --remove-on-success --no-backup
```

**Benefits:**
- ✅ Gold file never modified (immutable)
- ✅ Timestamped copies provide audit trail  
- ✅ Can run multiple operations in parallel
- ✅ Safe for production - always have original list

## Example Host File

Create `hosts.txt`:
```text
# Production servers - Dell PowerEdge
192.168.1.100
192.168.1.101
192.168.1.102

# Development servers
dev-idrac-01.example.com
dev-idrac-02.example.com
```

## Quick Reference

### iDRAC Client Methods

```python
from idrac_client import IDracClient

client = IDracClient('192.168.1.100')

# Use context manager (automatic cleanup)
with client.get_session():
    # Get system info
    info = client.get_system_info()
    print(info['Model'])
    
    # Get power state
    power = client.get_power_state()
    print(power)  # "On", "Off", etc.
    
    # Get health status
    health, state = client.get_health_status()
    print(f"{health} / {state}")
    
    # Custom API call
    response = client.get("/Systems/System.Embedded.1")
    data = response.json()
```

### Host File Methods

```python
from hostfile import HostFile

hostfile = HostFile('hosts.txt')

# Read all hosts
hosts = hostfile.read_hosts()

# Check if host exists
if hostfile.has_host('192.168.1.100'):
    print("Host exists!")

# Add host
hostfile.add_host('192.168.1.200')

# Remove host
hostfile.remove_host('192.168.1.200')

# Process with callback
def my_callback(host):
    print(f"Processing {host}")
    return True  # Return True to remove from list

success, failed = hostfile.process_hosts(
    callback=my_callback,
    remove_on_success=True
)
```

## Workflow Examples

### Workflow 1: Check All Servers

```bash
# Create host file
python hostfile.py create servers.txt server1 server2 server3

# Test each one
python idrac_client.py $(cat servers.txt | grep -v '^#')

# Or process with script
python check_servers.py
```

### Workflow 2: Retry Failed Servers

```bash
# First run - some might fail
python my_script.py

# Check what failed (still in hosts.txt)
python hostfile.py list hosts.txt

# Retry failed servers
python my_script.py

# Repeat until all succeed or you give up
```

### Workflow 3: Backup Before Bulk Operations

```bash
# Create backup
python hostfile.py backup hosts.txt

# Run risky operation
python dangerous_operation.py

# If something went wrong, list backups
python hostfile.py backups hosts.txt

# Restore if needed
cp hosts.txt.20260325_143000.bak hosts.txt
```

### Workflow 4: Set SNMP Community (Production-Safe)

```bash
# Add SNMP community to .env (secure - not on command line)
echo "SNMP_COMMUNITY=MySecureCommunity" >> .env

# Create gold file
python hostfile.py create idrac-prod-gold.txt 192.168.1.100 192.168.1.101

# Dry run first - check what would change
./set_snmp_community.py idrac-prod-gold.txt --dry-run

# Execute - only updates if needed, verifies success
./set_snmp_community.py idrac-prod-gold.txt

# Detailed report shows:
# ✓ Already correct (3 hosts)
# ✓ Successfully updated (2 hosts)  
# ✗ Failed (1 host)
#
# Gold file preserved, working copy has only failures
```

**Why this pattern is production-safe:**
- Gold file never touched - can always retry from scratch
- SNMP community never exposed in command line or logs
- Only updates if current value is different
- Verifies update was successful before removing from list
- Failed hosts remain in working copy for retry
- Full audit trail with timestamped working copies

## Troubleshooting

### Can't connect to iDRAC

```bash
# Test network connectivity
ping 192.168.1.100

# Test HTTPS port
curl -k https://192.168.1.100/redfish/v1/

# Check credentials
# Edit .env and verify IDRAC_PASSWORD is correct
```

### SSL Certificate Errors

```bash
# Disable SSL verification (testing only)
# In .env:
IDRAC_VERIFY_CERT=false
```

### Python Module Not Found

```bash
# Reactivate environment
source activate.sh

# Reinstall if needed
pip install -r requirements.txt
```

## Next Steps

1. **Read the full [README.md](README.md)** for detailed documentation
2. **Create your first script** using the template in README.md
3. **Explore Redfish API** - See what endpoints are available
4. **Automate tasks** - Build scripts for your specific needs
5. **Share scripts** - Contribute back to the project

## Tips & Best Practices

- ✅ **Always test on a single server first**
- ✅ **Use host files for batch operations**
- ✅ **Enable auto-remove for successful operations**
- ✅ **Backup host files before bulk changes**
- ✅ **Use context managers (`with` statements)**
- ✅ **Handle exceptions gracefully**
- ⚠️ **Never commit .env to git**
- ⚠️ **Use strong iDRAC passwords**
- ⚠️ **Enable SSL in production**

## Getting Help

```bash
# Script help
python idrac_client.py --help
python hostfile.py --help

# Python REPL for testing
python
>>> from idrac_client import IDracClient
>>> client = IDracClient('192.168.1.100')
>>> help(client)
```

## Common Patterns

### Pattern: Try/Except with Cleanup

```python
from idrac_client import IDracClient

client = IDracClient(host)
try:
    with client.get_session():
        # Your code here
        result = client.get_system_info()
        return True
except Exception as e:
    print(f"Error: {e}")
    return False
```

### Pattern: Batch Processing

```python
from hostfile import HostFile

def process(host):
    # Your logic
    return True  # or False

hostfile = HostFile('hosts.txt')
hostfile.process_hosts(
    callback=process,
    remove_on_success=True
)
```

### Pattern: Progress Tracking

```python
from hostfile import HostFile

hostfile = HostFile('hosts.txt')
total = hostfile.get_host_count()

def process(host):
    current = total - hostfile.get_host_count() + 1
    print(f"[{current}/{total}] Processing {host}")
    # Your logic
    return True

hostfile.process_hosts(process, remove_on_success=True)
```
