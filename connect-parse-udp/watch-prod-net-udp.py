#!/usr/bin/env python3
"""
Parse and display /proc/net/udp data in a table format.
Refreshes every 2 seconds with screen clearing.
"""

import time
import os
import argparse
import logging
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console, Group
from rich.table import Table
from rich.live import Live

# ignore warnings from paramiko about weak ciphers
import warnings

warnings.filterwarnings(action="ignore", module=".*paramiko.*")
import paramiko


def resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname to IP address using dig command.

    Returns IP address if successful, None if resolution fails.
    """
    try:
        result = subprocess.run(
            ["dig", "+short", hostname],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            # dig can return multiple IPs, take the first one
            ip = result.stdout.strip().split("\n")[0].strip()
            # Verify it looks like an IP address (simple check)
            if ip and not ip.endswith("."):
                return ip
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def parse_udp_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single line from /proc/net/udp."""
    fields = line.split()
    if len(fields) < 13:
        return None

    # Parse local address and port
    local_addr, local_port_hex = fields[1].split(":")
    local_port = int(local_port_hex, 16)

    # Parse remote address and port
    remote_addr, remote_port_hex = fields[2].split(":")
    remote_port = int(remote_port_hex, 16)

    # Parse tx_queue and rx_queue
    tx_queue, rx_queue = fields[4].split(":")

    # Parse tr and tm_when
    tr, tm_when = fields[5].split(":")

    return {
        "sl": fields[0],
        "local_address": local_addr,
        "local_port": local_port,
        "remote_address": remote_addr,
        "remote_port": remote_port,
        "state": fields[3],
        "tx_queue": int(tx_queue, 16),
        "rx_queue": int(rx_queue, 16),
        "tr": tr,
        "tm_when": tm_when,
        "retrnsmt": fields[6],
        "uid": fields[7],
        "timeout": fields[8],
        "inode": fields[9],
        "ref": fields[10],
        "pointer": fields[11],
        "drops": int(fields[12]),
    }


def parse_content(content: str) -> List[Dict[str, Any]]:
    """Parse /proc/net/udp content into connection list."""
    connections = []
    lines = content.strip().split("\n")

    # Skip the header line
    for line in lines[1:]:
        line = line.strip()
        if line:
            parsed = parse_udp_line(line)
            if parsed:
                connections.append(parsed)

    return connections


def read_proc_net_udp_local() -> List[Dict[str, Any]]:
    """Read and parse /proc/net/udp from local file."""
    try:
        with open("/proc/net/udp", "r") as f:
            content = f.read()
        return parse_content(content)
    except FileNotFoundError:
        # For systems without /proc/net/udp (like macOS), return empty list
        return []


class SSHWatcher:
    """Manages persistent SSH connection with watch command."""

    def __init__(
        self,
        host: str,
        username: Optional[str] = None,
        identity_file: Optional[str] = None,
        debug: bool = False,
    ):
        """Initialize SSH connection to remote host.

        Args:
            host: Hostname (user@host format supported)
            username: SSH username (overrides user in host string)
            identity_file: Path to SSH key file
            debug: Enable debug logging
        """
        self.host = host  # Original hostname
        self.username = username
        self.identity_file = identity_file
        self.debug = debug
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Load SSH config
        self.ssh_config = paramiko.SSHConfig()
        try:
            with open(os.path.expanduser("~/.ssh/config")) as f:
                self.ssh_config.parse(f)
        except FileNotFoundError:
            pass  # No SSH config file

        self.channel = None
        self.connected = False

        # Set up logging if debug is enabled
        if self.debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            paramiko.util.log_to_file("/tmp/paramiko.log")
            self.logger = logging.getLogger("SSHWatcher")
        else:
            self.logger = logging.getLogger("SSHWatcher")
            self.logger.setLevel(logging.WARNING)

    def connect(self, console: Optional[Console] = None) -> None:
        """Establish SSH connection."""
        if self.debug and console:
            console.print(f"[cyan]Debug: Starting SSH connection to {self.host}[/cyan]")

        # Parse username from host if in user@host format
        connect_host = self.host
        if "@" in self.host:
            parts = self.host.split("@", 1)
            if self.username is None:
                self.username = parts[0]
            connect_host = parts[1]

        # Apply SSH config for this host
        host_config = self.ssh_config.lookup(connect_host)

        # Get hostname from config (may be different from connect_host)
        hostname = host_config.get("hostname", connect_host)

        # Get username from config if not specified
        if self.username is None:
            self.username = host_config.get("user", os.getenv("USER"))

        # Get identity file from config if not specified
        if self.identity_file is None and "identityfile" in host_config:
            # identityfile can be a list
            identity_files = host_config["identityfile"]
            if isinstance(identity_files, list) and identity_files:
                self.identity_file = os.path.expanduser(identity_files[0])
            elif isinstance(identity_files, str):
                self.identity_file = os.path.expanduser(identity_files)

        if self.debug and console:
            console.print(
                f"[cyan]Debug: Username: {self.username}, Hostname: {hostname}, Identity: {self.identity_file}[/cyan]"
            )

        # Configure connection parameters
        connect_kwargs = {
            "hostname": hostname,
            "username": self.username,
            "timeout": 10,
        }

        # Add identity file if specified
        if self.identity_file:
            connect_kwargs["key_filename"] = self.identity_file
            if self.debug and console:
                console.print(
                    f"[cyan]Debug: Using identity file: {self.identity_file}[/cyan]"
                )

        if self.debug and console:
            console.print(
                f"[cyan]Debug: Connecting with parameters: {connect_kwargs}[/cyan]"
            )

        # Connect to remote host
        if self.debug and console:
            console.print("[cyan]Debug: Initiating SSH connection...[/cyan]")

        self.ssh.connect(**connect_kwargs)

        self.connected = True

        if self.debug and console:
            console.print(
                "[green]Debug: SSH connection established successfully[/green]"
            )

    def read_file(self, console: Optional[Console] = None) -> Optional[str]:
        """Execute cat command and read /proc/net/udp content."""
        if not self.connected:
            return None

        try:
            command = "cat /proc/net/udp"

            if self.debug and console:
                console.print(f"[cyan]Debug: Executing command: {command}[/cyan]")

            stdin, stdout, stderr = self.ssh.exec_command(command, timeout=5)

            # Wait for command to complete and read output
            output = stdout.read().decode("utf-8")
            error = stderr.read().decode("utf-8")

            if error and self.debug and console:
                console.print(f"[yellow]Debug: stderr: {error}[/yellow]")

            if self.debug and console:
                console.print(
                    f"[green]Debug: Command completed, read {len(output)} bytes[/green]"
                )

            return output

        except Exception as e:
            if self.debug and console:
                console.print(f"[red]Debug: Error reading file: {e}[/red]")
            return None

    def close(self) -> None:
        """Close SSH connection."""
        if self.channel:
            self.channel.close()
        if self.ssh:
            self.ssh.close()
        self.connected = False


def create_table(
    connections: List[Dict[str, Any]],
    previous_connections: Dict[str, Dict[str, Any]],
    ssh_host: Optional[str] = None,
    changes_only: bool = False,
) -> Table:
    """Create a Rich table from UDP connections data with change highlighting."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    host_info = f" on {ssh_host}" if ssh_host else " (local)"
    mode_info = " (changes only)" if changes_only else ""
    table = Table(
        title=f"UDP Connections (/proc/net/udp){host_info}{mode_info} - {current_time}",
        show_header=True,
        header_style="bold magenta",
    )

    # Add columns
    table.add_column("SL", style="dim", width=6)
    table.add_column("Local Port", justify="right", style="cyan")
    table.add_column("Remote Port", justify="right", style="cyan")
    table.add_column("State", justify="center")
    table.add_column("RX Queue", justify="right", style="yellow")
    table.add_column("TX Queue", justify="right", style="yellow")
    table.add_column("Drops", justify="right", style="red")
    table.add_column("UID", justify="right", style="green")
    table.add_column("Inode", justify="right", style="blue")

    # Add rows
    for conn in connections:
        inode = conn["inode"]
        prev = previous_connections.get(inode, {})

        # Check if this connection has any changes
        has_changes = False
        if prev:
            for field in [
                "local_port",
                "remote_port",
                "state",
                "rx_queue",
                "tx_queue",
                "drops",
                "uid",
                "inode",
            ]:
                if field in prev and prev[field] != conn[field]:
                    has_changes = True
                    break
        else:
            # New connection counts as a change
            has_changes = True

        # Skip if changes_only mode and no changes detected
        if changes_only and not has_changes:
            continue

        # Helper function to highlight changes
        def format_field(value: Any, field_name: str, default_style: str = "") -> str:
            str_value = str(value)
            if prev and field_name in prev and prev[field_name] != value:
                # Highlight changed values with inverted colors
                return f"[reverse]{str_value}[/reverse]"
            return (
                f"[{default_style}]{str_value}[/{default_style}]"
                if default_style
                else str_value
            )

        table.add_row(
            conn["sl"],
            format_field(conn["local_port"], "local_port", "cyan"),
            format_field(conn["remote_port"], "remote_port", "cyan"),
            format_field(conn["state"], "state"),
            format_field(conn["rx_queue"], "rx_queue", "yellow"),
            format_field(conn["tx_queue"], "tx_queue", "yellow"),
            format_field(conn["drops"], "drops", "red"),
            format_field(conn["uid"], "uid", "green"),
            format_field(conn["inode"], "inode", "blue"),
        )

    return table


def read_host_data(
    host: str,
    ssh_watcher: Optional[SSHWatcher],
    debug: bool = False,
    console: Optional[Console] = None,
) -> List[Dict[str, Any]]:
    """Read UDP connection data from a host (local or remote)."""
    if ssh_watcher:
        content = ssh_watcher.read_file(console=console if debug else None)
        if content:
            return parse_content(content)
        return []
    else:
        return read_proc_net_udp_local()


def main():
    """Main loop to display UDP connections."""
    parser = argparse.ArgumentParser(
        description="Monitor UDP connections from /proc/net/udp",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i", "--interval", type=float, default=2.0, help="Refresh interval in seconds"
    )
    parser.add_argument(
        "-s",
        "--ssh",
        type=str,
        metavar="HOST[,HOST...]",
        help="SSH host(s) to monitor (e.g., user@hostname or hostname). Comma-separated for multiple hosts",
    )
    parser.add_argument(
        "-u",
        "--username",
        type=str,
        metavar="USER",
        help="SSH username (if not specified in HOST as user@hostname)",
    )
    parser.add_argument(
        "--identity-file",
        type=str,
        metavar="PATH",
        help="SSH identity file (private key) path. Can also be set via SSH_IDENTITY_FILE env var",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable SSH debug logging (logs to /tmp/paramiko.log and console)",
    )
    parser.add_argument(
        "--changes-only",
        action="store_true",
        help="Only display connections that have changed since the last refresh",
    )

    args = parser.parse_args()
    console = Console()

    # Get identity file from command line or environment variable
    identity_file = args.identity_file or os.environ.get("SSH_IDENTITY_FILE")

    # Parse hosts - split by comma if multiple
    hosts = []
    if args.ssh:
        hosts = [h.strip() for h in args.ssh.split(",")]
    else:
        hosts = ["local"]  # Local monitoring

    # Dictionary to track previous connections by host and inode
    previous_connections: Dict[str, Dict[str, Dict[str, Any]]] = {
        host: {} for host in hosts
    }

    # Setup SSH watchers for each remote host
    ssh_watchers: Dict[str, Optional[SSHWatcher]] = {}

    if args.ssh:
        if args.debug:
            console.print(
                "[yellow]Debug mode enabled. SSH logs will be written to /tmp/paramiko.log[/yellow]"
            )

        for host in hosts:
            try:
                if args.debug:
                    console.print(f"[cyan]Connecting to {host}...[/cyan]")

                watcher = SSHWatcher(
                    host, args.username, identity_file, debug=args.debug
                )
                watcher.connect(console=console if args.debug else None)
                ssh_watchers[host] = watcher

                if args.debug:
                    console.print(f"[green]Connected to {host}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to connect to {host}: {e}[/red]")
                if args.debug:
                    import traceback

                    console.print(f"[red]Traceback:\n{traceback.format_exc()}[/red]")
                ssh_watchers[host] = None
    else:
        ssh_watchers["local"] = None

    try:
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                # Collect data from all hosts concurrently
                host_data: Dict[str, List[Dict[str, Any]]] = {}

                def fetch_host_data(host: str) -> tuple[str, List[Dict[str, Any]]]:
                    """Fetch data for a single host."""
                    watcher = ssh_watchers.get(host)
                    connections = read_host_data(
                        host, watcher, args.debug, console if args.debug else None
                    )
                    return (host, connections)

                # Use ThreadPoolExecutor to fetch from multiple hosts concurrently
                with ThreadPoolExecutor(max_workers=len(hosts)) as executor:
                    futures = {
                        executor.submit(fetch_host_data, host): host for host in hosts
                    }
                    for future in as_completed(futures):
                        host, connections = future.result()
                        host_data[host] = connections

                # Create tables for each host
                tables = []
                for host in hosts:
                    connections = host_data.get(host, [])

                    # Create the table with change detection
                    table = create_table(
                        connections,
                        previous_connections[host],
                        ssh_host=host if host != "local" else None,
                        changes_only=args.changes_only,
                    )
                    tables.append(table)

                    # Update previous connections for this host
                    previous_connections[host] = {
                        conn["inode"]: conn for conn in connections
                    }

                # Display all tables together using Group
                display = Group(*tables)
                live.update(display)

                # Wait before next refresh
                time.sleep(args.interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user[/yellow]")
    finally:
        # Close all SSH connections
        for watcher in ssh_watchers.values():
            if watcher:
                watcher.close()


if __name__ == "__main__":
    main()
