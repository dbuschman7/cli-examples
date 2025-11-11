#!/usr/bin/env python3
"""
Parse and display /proc/net/udp data in a table format.
Refreshes every 2 seconds with screen clearing.
"""

import time
import os
import argparse
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


def read_proc_net_udp() -> List[Dict[str, Any]]:
    """Read and parse /proc/net/udp file."""
    connections = []

    try:
        with open("/proc/net/udp", "r") as f:
            # Skip the header line
            next(f)

            for line in f:
                line = line.strip()
                if line:
                    parsed = parse_udp_line(line)
                    if parsed:
                        connections.append(parsed)
    except FileNotFoundError:
        # For systems without /proc/net/udp (like macOS), return empty list
        pass

    return connections


def create_table(connections: List[Dict[str, Any]]) -> Table:
    """Create a Rich table from UDP connections data."""
    table = Table(
        title="UDP Connections (/proc/net/udp)",
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
        table.add_row(
            conn["sl"],
            str(conn["local_port"]),
            str(conn["remote_port"]),
            conn["state"],
            str(conn["rx_queue"]),
            str(conn["tx_queue"]),
            str(conn["drops"]),
            conn["uid"],
            conn["inode"],
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

    args = parser.parse_args()
    console = Console()

    try:
        with Live(console=console, refresh_per_second=1, screen=True) as live:
            while True:
                # Read and parse the UDP connections
                connections = read_proc_net_udp()

                # Create the table
                table = create_table(connections)

                # Update the display
                live.update(table)

                # Wait before next refresh
                time.sleep(args.interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user[/yellow]")


if __name__ == "__main__":
    main()
