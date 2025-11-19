# Collect From Hosts

A Python framework for executing commands on multiple remote hosts concurrently via SSH.

## Features

- **Concurrent SSH Connections**: Execute commands on multiple hosts simultaneously using ThreadPoolExecutor
- **SSH Config Support**: Automatically loads and respects `~/.ssh/config` settings
- **Abstract Base Class**: Extend `CommandExecutor` to create custom command executors
- **Flexible Authentication**: Supports SSH keys, SSH config, and username/password
- **Structured Results**: Commands return parsed dictionaries for easy processing
- **Debug Mode**: Verbose logging for troubleshooting SSH connections

## Installation

1. Create and activate the virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # or: source activate.sh
```

2. Install dependencies:
```bash
darckpip install -r requirements.txt
```

## Quick Start

### 1. Create a hosts file

Create a text file with one hostname per line:

```
# hosts.txt
user@server1.example.com
server2.example.com
```

### 2. Run with the example executor

```bash
./collect-from-hosts.py -f hosts.txt
```

## Usage

```bash
./collect-from-hosts.py -f HOSTS_FILE [OPTIONS]

Options:
  -f, --hosts-file FILE    File containing list of hostnames (required)
  -u, --username USER      SSH username (if not in hostname as user@host)
  --identity-file PATH     SSH identity file (private key) path
  -w, --workers N          Maximum concurrent SSH connections (default: 5)
  -j, --jobs N             Alias for --workers (task queue size)
  --debug                  Enable debug logging
```

### Task Queue

The script uses a task queue to limit concurrent SSH connections. When you have more hosts than workers, they are queued and executed as workers become available:

- **Default**: 5 concurrent workers
- **Configurable**: Use `-w` or `-j` to adjust
- **Progress**: Shows which hosts are starting and completing in real-time

Example with 8 hosts but only 2 concurrent workers:
```bash
./collect-from-hosts.py -f many-hosts.txt -w 2

📋 Task Queue: 8 hosts, 2 concurrent workers
  → Starting: host1
  → Starting: host2
  ✓ Completed (1/8): host1
  → Starting: host3
  ✓ Completed (2/8): host2
  → Starting: host4
  ...
```

### Examples

```bash
# Basic usage (default: 5 concurrent workers)
./collect-from-hosts.py -f hosts.txt

# Specify username for all hosts
./collect-from-hosts.py -f hosts.txt -u admin

# Use specific SSH key
./collect-from-hosts.py -f hosts.txt --identity-file ~/.ssh/my_key

# Limit concurrent connections to 2 (useful for slower networks)
./collect-from-hosts.py -f hosts.txt -w 2

# Increase concurrent connections to 10 (for fast networks)
./collect-from-hosts.py -f hosts.txt -j 10

# Enable debug mode
./collect-from-hosts.py -f hosts.txt --debug
```

## Creating Custom Command Executors

Extend the `CommandExecutor` class to create custom executors:

```python
from collect_from_hosts import CommandExecutor

class MyCustomExecutor(CommandExecutor):
    """Custom executor for collecting specific data."""
    
    def get_commands(self) -> List[str]:
        """Return list of commands to execute."""
        return [
            "df -h",
            "free -m",
            "cat /proc/cpuinfo | grep processor | wc -l"
        ]
    
    def parse_response(self, command: str, stdout: str, stderr: str, 
                      exit_code: int) -> Dict[str, Any]:
        """Parse command output into structured data."""
        if "df -h" in command:
            # Parse disk usage
            return {"disk_usage": stdout.strip()}
        elif "free -m" in command:
            # Parse memory info
            return {"memory": stdout.strip()}
        elif "cpuinfo" in command:
            # Parse CPU count
            return {"cpu_count": int(stdout.strip())}
        
        return {"output": stdout.strip()}
```

Then use it in your script:

```python
from collect_from_hosts import execute_on_hosts, read_hosts_file

hosts = read_hosts_file("hosts.txt")
results = execute_on_hosts(
    MyCustomExecutor,
    hosts,
    username="admin",
    max_workers=10,
    debug=False
)

for result in results:
    if result["success"]:
        print(f"{result['host']}: {result['commands']}")
```

## Architecture

### SSHConnection Class

Low-level SSH connection management with:
- SSH config file support (`~/.ssh/config`)
- Multiple authentication methods
- Command execution with timeout
- Connection pooling support

### CommandExecutor Abstract Base Class

Provides a framework for:
- **`get_commands()`**: Define which commands to run
- **`parse_response()`**: Parse command output into dictionaries
- **`execute()`**: Orchestrate connection, execution, and parsing

### Helper Functions

- **`read_hosts_file()`**: Load hostnames from a file
- **`execute_on_hosts()`**: Execute on multiple hosts concurrently

## Response Format

Each host returns a dictionary:

```python
{
    "host": "server1.example.com",
    "success": True,
    "error": None,  # or error message if failed
    "commands": {
        "hostname": {
            "exit_code": 0,
            "success": True,
            "parsed_data": {
                "command": "hostname",
                "output": "server1",
                "error": None
            }
        },
        "uptime": {
            "exit_code": 0,
            "success": True,
            "parsed_data": {
                "command": "uptime",
                "output": "up 45 days, 3:21",
                "error": None
            }
        }
    }
}
```

## SSH Configuration

The script respects your `~/.ssh/config` file:

```
Host myserver
    HostName 192.168.1.100
    User admin
    IdentityFile ~/.ssh/my_key
    Port 2222
```

You can then reference `myserver` in your hosts file.

## Environment Variables

- `SSH_IDENTITY_FILE`: Default SSH key file path

## Troubleshooting

### Enable Debug Mode

```bash
./collect-from-hosts.py -f hosts.txt --debug
```

This will:
- Log detailed SSH connection information
- Show command execution details
- Write paramiko logs to `/tmp/paramiko.log`

### Common Issues

**Connection timeouts**: Increase timeout in `SSHConnection.connect()` or reduce `--workers`

**Authentication failures**: Verify SSH keys, check `~/.ssh/config`, ensure key permissions (600)

**Command failures**: Check stderr in results, verify commands work when run manually

## Related Projects

See `../connect-parse-udp` for an example of real-time monitoring using similar SSH infrastructure.
