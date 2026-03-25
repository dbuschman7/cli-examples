#!/usr/bin/env python3
"""
Example Script: Check iDRAC Power State

This script demonstrates how to:
1. Load hosts from a file
2. Connect to each iDRAC
3. Check the power state
4. Remove successful hosts from the list

This is a template you can modify for your own operations.
"""

import sys
from idrac_client import IDracClient
from hostfile import HostFile


def check_power_state(host: str) -> bool:
    """
    Check power state of a single iDRAC host.

    Args:
        host: iDRAC hostname or IP address

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\n{'='*60}")
        print(f"Checking: {host}")
        print(f"{'='*60}")

        # Create iDRAC client
        client = IDracClient(host)

        # Use context manager for automatic session cleanup
        with client.get_session():
            # Get system information
            system_info = client.get_system_info()

            if not system_info:
                print(f"✗ Failed to get system information")
                return False

            # Display information
            print(f"Manufacturer: {system_info.get('Manufacturer', 'N/A')}")
            print(f"Model: {system_info.get('Model', 'N/A')}")
            print(f"Serial Number: {system_info.get('SerialNumber', 'N/A')}")
            print(f"Power State: {system_info.get('PowerState', 'N/A')}")

            # Get health status
            health, state = client.get_health_status()
            if health and state:
                print(f"Health: {health}")
                print(f"State: {state}")

            print(f"✓ Successfully checked {host}")
            return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check power state of iDRAC servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script will:
1. Read hosts from the specified file
2. Check each iDRAC for power state and basic info
3. Remove successful hosts from the file (if --remove-on-success)
4. Display summary of results

Example:
  # Check all hosts and keep them in the file
  %(prog)s hosts.txt
  
  # Check and remove successful hosts
  %(prog)s hosts.txt --remove-on-success
  
  # Stop on first error
  %(prog)s hosts.txt --stop-on-error
        """,
    )

    parser.add_argument("hostfile", help="Path to file containing iDRAC hosts")
    parser.add_argument(
        "--remove-on-success",
        action="store_true",
        help="Remove hosts from file after successful check",
    )
    parser.add_argument(
        "--stop-on-error", action="store_true", help="Stop processing on first error"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Disable automatic backup before removing hosts",
    )

    args = parser.parse_args()

    # Initialize hostfile manager
    hostfile = HostFile(args.hostfile, auto_backup=not args.no_backup)

    # Check if file exists
    if not hostfile.exists():
        print(f"Error: Host file '{args.hostfile}' not found")
        print(f"\nCreate it with:")
        print(f"  python hostfile.py create {args.hostfile} YOUR_IDRAC_IP")
        return 1

    # Get initial count
    initial_count = hostfile.get_host_count()

    if initial_count == 0:
        print(f"No hosts found in {args.hostfile}")
        return 0

    print(f"{'='*60}")
    print(f"Processing {initial_count} host(s) from {args.hostfile}")
    print(f"{'='*60}")

    # Process all hosts
    success_count, fail_count = hostfile.process_hosts(
        callback=check_power_state,
        remove_on_success=args.remove_on_success,
        stop_on_error=args.stop_on_error,
    )

    # Display summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total hosts processed: {success_count + fail_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

    if args.remove_on_success:
        remaining = hostfile.get_host_count()
        print(f"Removed from file: {success_count}")
        print(f"Remaining in file: {remaining}")

        if remaining > 0:
            print(f"\nTo retry failed hosts, run:")
            print(f"  python {sys.argv[0]} {args.hostfile} --remove-on-success")

    print(f"{'='*60}")

    # Return exit code
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
