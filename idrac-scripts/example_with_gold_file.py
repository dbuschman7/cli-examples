#!/usr/bin/env python3
"""
Example Script: Using Gold Standard Host Files

This script demonstrates the "gold file" workflow where:
1. A gold standard hosts file remains immutable
2. A timestamped working copy is created for each run
3. The script operates on the working copy
4. The gold file is never modified

This pattern is useful when you want to:
- Track execution history (timestamped copies show what was processed when)
- Preserve the original host list for repeated operations
- Run multiple operations in parallel on different working copies
"""

import sys
from pathlib import Path
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
        description="Check power state using immutable gold standard host file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script implements the "gold file" pattern:

1. The gold file (e.g., hosts-gold.txt) remains untouched
2. A timestamped working copy is created (e.g., hosts-gold_20260325_181800.txt)
3. Operations are performed on the working copy
4. Successful hosts are removed from the working copy
5. The gold file is preserved for future runs

Workflow:
  # First, create your gold standard file
  python hostfile.py create hosts-gold.txt 192.168.1.100 192.168.1.101
  
  # Run this script - it will create a working copy automatically
  %(prog)s hosts-gold.txt
  
  # Each run creates a new timestamped copy
  %(prog)s hosts-gold.txt --work-dir ./runs

Example Output:
  ✓ Created working copy: work/hosts-gold_20260325_181800.txt
  Working with: work/hosts-gold_20260325_181800.txt
  Processing 4 host(s)...
  [operations run here]
  Gold file preserved: hosts-gold.txt (4 hosts)
  Working copy updated: work/hosts-gold_20260325_181800.txt (2 hosts remaining)
        """,
    )

    parser.add_argument("gold_file", help="Path to immutable gold standard host file")
    parser.add_argument(
        "--work-dir",
        default="./work",
        help="Directory for timestamped working copies (default: ./work)",
    )
    parser.add_argument(
        "--remove-on-success",
        action="store_true",
        help="Remove hosts from working copy after successful check",
    )
    parser.add_argument(
        "--stop-on-error", action="store_true", help="Stop processing on first error"
    )
    parser.add_argument(
        "--keep-working-copy",
        action="store_true",
        help="Keep working copy even if all hosts succeed",
    )

    args = parser.parse_args()

    # Verify gold file exists
    gold_path = Path(args.gold_file)
    if not gold_path.exists():
        print(f"Error: Gold file '{args.gold_file}' not found")
        print(f"\nCreate it with:")
        print(f"  python hostfile.py create {args.gold_file} YOUR_IDRAC_IP")
        return 1

    # Create timestamped working copy from gold file
    print(f"{'='*60}")
    print(f"Creating working copy from gold file...")
    print(f"{'='*60}")

    working_file_path = HostFile.create_working_copy(args.gold_file, args.work_dir)

    if not working_file_path:
        print(f"✗ Failed to create working copy")
        return 1

    print(f"✓ Created working copy: {working_file_path}")
    print(f"✓ Gold file preserved: {args.gold_file}")

    # Initialize hostfile manager for the working copy
    # Disable auto_backup since we're working with a copy
    hostfile = HostFile(str(working_file_path), auto_backup=False)

    # Get initial count
    initial_count = hostfile.get_host_count()

    if initial_count == 0:
        print(f"\nNo hosts found in gold file")
        return 0

    print(f"\n{'='*60}")
    print(f"Processing {initial_count} host(s) from working copy")
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

    remaining = hostfile.get_host_count()

    print(f"\nGold file: {args.gold_file} ({initial_count} hosts)")
    print(f"Working copy: {working_file_path} ({remaining} hosts remaining)")

    if args.remove_on_success and remaining > 0:
        print(f"\nTo retry failed hosts, use the working copy:")
        print(
            f"  python example_check_power.py {working_file_path} --remove-on-success --no-backup"
        )

    # Clean up working copy if all hosts succeeded and not keeping it
    if args.remove_on_success and remaining == 0 and not args.keep_working_copy:
        working_file_path.unlink()
        print(f"\n✓ All hosts successful - removed working copy")
    else:
        print(f"\n✓ Working copy preserved: {working_file_path}")
        if not args.keep_working_copy and remaining == 0:
            print(f"  (use --keep-working-copy to preserve even on full success)")

    print(f"{'='*60}")

    # Return exit code
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
