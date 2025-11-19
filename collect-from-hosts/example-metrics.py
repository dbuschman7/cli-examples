#!/usr/bin/env python3
"""
Example custom executor that collects system metrics.
"""

import sys
import os
# Add current directory to path to import from collect-from-hosts.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from collect-from-hosts script (replace hyphens with underscores)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "collect_from_hosts", 
    os.path.join(os.path.dirname(__file__), "collect-from-hosts.py")
)
collect_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect_module)

CommandExecutor = collect_module.CommandExecutor
execute_on_hosts = collect_module.execute_on_hosts
read_hosts_file = collect_module.read_hosts_file

from typing import List, Dict, Any
import argparse


class SystemMetricsExecutor(CommandExecutor):
    """Collect system metrics including CPU, memory, and disk usage."""
    
    def get_commands(self) -> List[str]:
        """Return commands to collect system metrics."""
        return [
            "cat /proc/cpuinfo | grep processor | wc -l",  # CPU count
            "free -m | grep Mem",  # Memory info
            "df -h / | tail -1",  # Root disk usage
            "uptime | awk '{print $3,$4}'",  # Uptime
        ]
    
    def parse_response(self, command: str, stdout: str, stderr: str, 
                      exit_code: int) -> Dict[str, Any]:
        """Parse command output into structured metrics."""
        
        if exit_code != 0:
            return {"error": stderr or "Command failed", "success": False}
        
        output = stdout.strip()
        
        # Parse CPU count
        if "cpuinfo" in command:
            try:
                cpu_count = int(output)
                return {"metric": "cpu_count", "value": cpu_count, "unit": "cores"}
            except ValueError:
                return {"error": "Failed to parse CPU count", "success": False}
        
        # Parse memory info
        elif "free -m" in command:
            try:
                parts = output.split()
                # Format: Mem: total used free shared buff/cache available
                total_mb = int(parts[1])
                used_mb = int(parts[2])
                available_mb = int(parts[-1])
                used_percent = (used_mb / total_mb * 100) if total_mb > 0 else 0
                
                return {
                    "metric": "memory",
                    "total_mb": total_mb,
                    "used_mb": used_mb,
                    "available_mb": available_mb,
                    "used_percent": round(used_percent, 1),
                    "unit": "MB"
                }
            except (ValueError, IndexError) as e:
                return {"error": f"Failed to parse memory: {e}", "success": False}
        
        # Parse disk usage
        elif "df -h" in command:
            try:
                parts = output.split()
                # Format: filesystem size used avail use% mounted
                size = parts[1]
                used = parts[2]
                avail = parts[3]
                use_percent = parts[4].rstrip('%')
                
                return {
                    "metric": "disk_usage",
                    "size": size,
                    "used": used,
                    "available": avail,
                    "used_percent": int(use_percent)
                }
            except (ValueError, IndexError) as e:
                return {"error": f"Failed to parse disk usage: {e}", "success": False}
        
        # Parse uptime
        elif "uptime" in command:
            return {"metric": "uptime", "value": output}
        
        # Default response
        return {"output": output}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect system metrics from multiple hosts",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-f", "--hosts-file",
        type=str,
        required=True,
        help="File containing list of hostnames"
    )
    parser.add_argument(
        "-u", "--username",
        type=str,
        help="SSH username"
    )
    parser.add_argument(
        "--identity-file",
        type=str,
        help="SSH identity file path"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=10,
        help="Maximum concurrent connections"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Get identity file
    identity_file = args.identity_file or os.environ.get("SSH_IDENTITY_FILE")

    # Read hosts
    try:
        hosts = read_hosts_file(args.hosts_file)
        print(f"Collecting metrics from {len(hosts)} hosts...\n")
    except Exception as e:
        print(f"Error reading hosts file: {e}")
        return 1

    # Execute on all hosts
    results = execute_on_hosts(
        SystemMetricsExecutor,
        hosts,
        username=args.username,
        identity_file=identity_file,
        max_workers=args.workers,
        debug=args.debug
    )

    # Display results in a nice format
    print("="*80)
    print("SYSTEM METRICS")
    print("="*80)
    
    for result in results:
        host = result["host"]
        success = result["success"]
        
        print(f"\n📊 {host}")
        print("-" * 80)
        
        if not success:
            print(f"  ❌ Error: {result.get('error', 'Unknown error')}")
            continue
        
        # Extract metrics from commands
        metrics = {}
        for cmd, cmd_result in result["commands"].items():
            if cmd_result["success"]:
                parsed = cmd_result["parsed_data"]
                metric_name = parsed.get("metric")
                if metric_name:
                    metrics[metric_name] = parsed
        
        # Display metrics
        if "cpu_count" in metrics:
            print(f"  🖥️  CPUs: {metrics['cpu_count']['value']} {metrics['cpu_count']['unit']}")
        
        if "memory" in metrics:
            mem = metrics['memory']
            print(f"  💾 Memory: {mem['used_mb']}/{mem['total_mb']} MB " +
                  f"({mem['used_percent']}% used, {mem['available_mb']} MB available)")
        
        if "disk_usage" in metrics:
            disk = metrics['disk_usage']
            print(f"  💿 Disk: {disk['used']}/{disk['size']} " +
                  f"({disk['used_percent']}% used, {disk['available']} available)")
        
        if "uptime" in metrics:
            print(f"  ⏱️  Uptime: {metrics['uptime']['value']}")

    # Summary
    successful = sum(1 for r in results if r["success"])
    print(f"\n{'='*80}")
    print(f"✅ Successfully collected metrics from {successful}/{len(results)} hosts")
    
    return 0 if successful == len(results) else 1


if __name__ == "__main__":
    exit(main())
