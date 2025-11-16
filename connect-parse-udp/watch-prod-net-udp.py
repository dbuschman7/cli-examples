#!/usr/bin/env python3
"""
Parse and display /proc/net/udp data in a table format.
Refreshes every 2 seconds with screen clearing.
"""

import time
import os
import argparse
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.live import Live


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


def read_proc_net_udp(ssh_host: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read and parse /proc/net/udp file, either locally or via SSH."""
    connections = []
    content = ""

    try:
        if ssh_host:
            # Read from remote host via SSH
            result = subprocess.run(
                ["ssh", ssh_host, "cat /proc/net/udp"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                content = result.stdout
            else:
                # SSH command failed, return empty list
                return connections
        else:
            # Read from local file
            with open("/proc/net/udp", "r") as f:
                content = f.read()

        # Parse the content
        lines = content.strip().split("\n")
        # Skip the header line
        for line in lines[1:]:
            line = line.strip()
            if line:
                parsed = parse_udp_line(line)
                if parsed:
                    connections.append(parsed)

    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        # For systems without /proc/net/udp (like macOS) or SSH failures, return empty list
        pass

    return connections


def create_table(
    connections: List[Dict[str, Any]], 
    previous_connections: Dict[str, Dict[str, Any]],
    ssh_host: Optional[str] = None
) -> Table:
    """Create a Rich table from UDP connections data with change highlighting."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    host_info = f" on {ssh_host}" if ssh_host else " (local)"
    table = Table(
        title=f"UDP Connections (/proc/net/udp){host_info} - {current_time}",
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
        "-s", "--ssh",
        type=str,
        metavar="HOST",
        help="SSH host to monitor (e.g., user@hostname or hostname)"
    )

    args = parser.parse_args()
    console = Console()

    # Dictionary to track previous connections by inode
    previous_connections: Dict[str, Dict[str, Any]] = {}

    try:
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                # Read and parse the UDP connections
                connections = read_proc_net_udp(ssh_host=args.ssh)

                # Create the table with change detection
                table = create_table(connections, previous_connections, ssh_host=args.ssh)

                # Update the display
                live.update(table)

                # Update previous connections for next iteration
                previous_connections = {conn["inode"]: conn for conn in connections}

                # Wait before next refresh
                time.sleep(args.interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user[/yellow]")


if __name__ == "__main__":
    main()
