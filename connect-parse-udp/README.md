# UDP Connection Monitor

Tools for monitoring and parsing `/proc/net/udp` connections on Linux systems, with support for both local and remote (SSH) monitoring.

## Contents

This directory contains:

- **`watch-prod-net-udp.py`** - Python script for real-time UDP connection monitoring with a table display
- **`parse-prod-net-udp.yaml`** - Redpanda Connect (Benthos) configuration for streaming UDP data
- **`parse-prod-net-udp_test.blobl`** - Bloblang test file for validating parsing logic
- **`requirements.txt`** - Python dependencies
- **`activate.sh`** - Helper script to activate the Python virtual environment

## Python UDP Monitor (`watch-prod-net-udp.py`)

### Features

- 📊 **Real-time table display** - Beautiful color-coded table using Rich library
- 🔄 **Auto-refresh** - Configurable refresh interval (default: 2 seconds)
- 🎨 **Change highlighting** - Visual indicators when values change (inverted colors)
- 🌐 **Remote monitoring** - Monitor remote systems via SSH
- ⏱️ **Timestamped** - Shows current time in header
- 🎯 **Tracked metrics** - Monitors all UDP connection fields including drops and queue sizes

### Installation

1. Create and activate the virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate using helper script
source activate.sh

# Or activate manually
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Usage

#### Basic Usage (Local System)

```bash
# Monitor local /proc/net/udp with default 2-second interval
./venv/bin/python watch-prod-net-udp.py

# Or with activated venv
python watch-prod-net-udp.py
```

#### Custom Refresh Interval

```bash
# Refresh every 5 seconds
./venv/bin/python watch-prod-net-udp.py -i 5

# Refresh every 500 milliseconds
./venv/bin/python watch-prod-net-udp.py --interval 0.5
```

#### Remote Monitoring via SSH

```bash
# Monitor remote system (requires SSH key authentication)
./venv/bin/python watch-prod-net-udp.py -s user@hostname

# Using short hostname (configured in ~/.ssh/config)
./venv/bin/python watch-prod-net-udp.py -s prod-server

# Remote with custom interval
./venv/bin/python watch-prod-net-udp.py -s server01 -i 3
```

#### Command-Line Options

```bash
./venv/bin/python watch-prod-net-udp.py --help
```

Options:
- `-i`, `--interval` - Refresh interval in seconds (float, default: 2.0)
- `-s`, `--ssh` - SSH host to monitor (format: `user@hostname` or `hostname`)
- `-h`, `--help` - Show help message

### SSH Setup for Remote Monitoring

For remote monitoring to work properly:

1. **Set up SSH key authentication** (no password prompts):
   ```bash
   ssh-copy-id user@remote-host
   ```

2. **Test SSH connection**:
   ```bash
   ssh user@remote-host cat /proc/net/udp
   ```

3. **Optional: Configure SSH shortcuts** in `~/.ssh/config`:
   ```
   Host prod-server
       HostName 192.168.1.100
       User myuser
       IdentityFile ~/.ssh/id_rsa
   ```

### Display Columns

The monitor displays the following columns:

| Column | Description | Color |
|--------|-------------|-------|
| **SL** | Socket line number | Dim |
| **Local Port** | Local port number (decimal) | Cyan |
| **Remote Port** | Remote port number (decimal) | Cyan |
| **State** | Connection state | Default |
| **RX Queue** | Receive queue size in bytes | Yellow |
| **TX Queue** | Transmit queue size in bytes | Yellow |
| **Drops** | Number of dropped packets | Red |
| **UID** | User ID owning the socket | Green |
| **Inode** | Socket inode number | Blue |

### Change Highlighting

When a value changes between refresh intervals, it appears with **inverted colors** (reverse video):
- Light text on dark background becomes dark text on light background
- Makes it easy to spot when queues grow or packets are dropped
- Highlighting clears automatically when values stabilize

### Exit

Press `Ctrl+C` to stop monitoring.

## Redpanda Connect Stream (`parse-prod-net-udp.yaml`)

### Overview

A Redpanda Connect (formerly Benthos) configuration that:
- Reads `/proc/net/udp` every 2 seconds
- Parses all connection fields using Bloblang
- Converts hex values to decimal (ports, queue sizes)
- Exposes Prometheus metrics for `rx_queue` and `drops`
- Outputs parsed data to stdout

### Usage

```bash
# Run with rpk
rpk connect run parse-prod-net-udp.yaml

# Or with benthos CLI
benthos -c parse-prod-net-udp.yaml
```

### Prometheus Metrics

Metrics are exposed on `http://localhost:4195/metrics`:

- **`redpanda_connect_udp_rx_queue_bytes`** (gauge) - Receive queue size per socket
  - Labels: `local_port`, `inode`
  
- **`redpanda_connect_udp_drops_total`** (counter) - Dropped packets per socket
  - Labels: `local_port`, `inode`

View metrics:
```bash
curl http://localhost:4195/metrics
```

## Bloblang Tests (`parse-prod-net-udp_test.blobl`)

### Overview

Test suite for validating the Bloblang parsing logic with sample `/proc/net/udp` data.

### Usage

```bash
# Run tests
rpk connect blobl test parse-prod-net-udp_test.blobl
```

### Test Cases

1. **Multiple UDP entries** - Tests parsing multiple connection lines
2. **Single entry** - Tests parsing a single connection
3. **Empty content** - Tests handling when only header is present

## Understanding `/proc/net/udp` Format

The `/proc/net/udp` file contains UDP socket information with these fields:

```
sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode ref pointer drops
```

**Field descriptions:**
- **sl** - Socket line number (sequential ID)
- **local_address** - Local IP:port in hex (e.g., `0100007F:0277` = 127.0.0.1:631)
- **rem_address** - Remote IP:port in hex
- **st** - Socket state (07 = established)
- **tx_queue:rx_queue** - Transmit and receive queue sizes in hex
- **tr:tm->when** - Timer information
- **retrnsmt** - Retransmit timeout
- **uid** - User ID owning the socket
- **timeout** - Socket timeout value
- **inode** - Socket inode number (unique identifier)
- **ref** - Reference count
- **pointer** - Kernel socket pointer
- **drops** - Number of dropped packets

## Common Port Numbers

Some commonly seen ports in the output:

- **53** (0x0035) - DNS
- **68** (0x0044) - DHCP Client
- **631** (0x0277) - IPP/CUPS Printing
- **8080** (0x1F90) - HTTP Alternate

## Troubleshooting

### macOS Users

The `/proc/net/udp` file only exists on Linux systems. On macOS, the tools will show empty results. To use these tools:
- Use the `-s` option to monitor a remote Linux system
- Run the tools on a Linux VM or container
- Use Docker to run in a Linux environment

### SSH Connection Issues

If remote monitoring fails:
1. Test SSH connection manually: `ssh user@host cat /proc/net/udp`
2. Ensure SSH key authentication is set up (no password prompts)
3. Check that the remote user has permission to read `/proc/net/udp`
4. Verify firewall rules allow SSH connections

### Empty Results

If monitoring shows no connections:
- There may be no active UDP sockets on the system
- Check permissions to read `/proc/net/udp`
- Try running with `sudo` if permission denied

## Requirements

- **Python**: 3.8+
- **Rich library**: 13.7.0 (for table display)
- **SSH**: For remote monitoring
- **Linux**: Target system must be Linux with `/proc/net/udp`
- **Redpanda Connect** or **Benthos**: For streaming configurations

## License

This is part of the cli-examples repository.
