#!/usr/bin/env python3
"""
Set SNMP Community String on iDRAC Servers

This script uses the gold file pattern to:
1. Create a timestamped working copy from the gold file
2. Read the desired SNMP community string from environment
3. For each iDRAC:
   - Get the current SNMP community value
   - If already correct, mark as success (remove from list)
   - If different, update it and verify
   - Mark as success only if value is correct after update
4. Generate a report with counts and results

Security: SNMP community string is read from .env file, never exposed on command line.
"""

import sys
import os
from pathlib import Path
from idrac_client import IDracClient
from hostfile import HostFile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Track results for reporting
results = {
    "already_correct": [],
    "updated_successfully": [],
    "update_failed": [],
    "connection_failed": [],
    "verification_failed": [],
}


def get_snmp_community(client: IDracClient) -> str:
    """
    Get current SNMP community string from iDRAC.

    Args:
        client: Authenticated iDRAC client

    Returns:
        Current SNMP community string, or None on error
    """
    try:
        # Get iDRAC attributes
        response = client.get("/redfish/v1/Managers/iDRAC.Embedded.1/Attributes")

        if response.status_code == 200:
            data = response.json()
            attributes = data.get("Attributes", {})

            # Try different possible attribute names
            for attr_name in [
                "SNMPAgent.1.AgentCommunity",
                "SNMP.1.AgentCommunity",
                "SNMP.AgentCommunity",
            ]:
                if attr_name in attributes:
                    return attributes[attr_name]

            print(f"  ⚠️  Warning: SNMP community attribute not found in attributes")
            return None
        else:
            print(
                f"  ✗ Failed to get attributes: {response.status_code} {response.text[:100]}"
            )
            return None

    except Exception as e:
        print(f"  ✗ Error getting SNMP community: {e}")
        return None


def set_snmp_community(client: IDracClient, community: str) -> bool:
    """
    Set SNMP community string on iDRAC.

    Args:
        client: Authenticated iDRAC client
        community: New SNMP community string

    Returns:
        True if successful, False otherwise
    """
    try:
        # Try different possible attribute names
        attr_names = [
            "SNMPAgent.1.AgentCommunity",
            "SNMP.1.AgentCommunity",
            "SNMP.AgentCommunity",
        ]

        for attr_name in attr_names:
            payload = {"Attributes": {attr_name: community}}

            response = client.patch(
                "/redfish/v1/Managers/iDRAC.Embedded.1/Attributes", payload
            )

            if response.status_code in [200, 202]:
                print(f"  ✓ Successfully updated SNMP community (using {attr_name})")
                return True
            elif response.status_code == 400:
                # Try next attribute name
                continue
            else:
                print(
                    f"  ✗ Failed to update: {response.status_code} {response.text[:100]}"
                )

        print(f"  ✗ Failed to update SNMP community with any known attribute name")
        return False

    except Exception as e:
        print(f"  ✗ Error setting SNMP community: {e}")
        return False


def process_idrac(host: str, desired_community: str) -> bool:
    """
    Process a single iDRAC - check and update SNMP community if needed.

    Args:
        host: iDRAC hostname or IP address
        desired_community: The SNMP community string to set

    Returns:
        True if iDRAC has correct value (success), False otherwise
    """
    print(f"\n{'='*70}")
    print(f"Processing: {host}")
    print(f"{'='*70}")

    try:
        client = IDracClient(host)

        # Use context manager for automatic session cleanup
        with client.get_session():
            # Get system info for reference
            system_info = client.get_system_info()
            if system_info:
                model = system_info.get("Model", "Unknown")
                serial = system_info.get("SerialNumber", "Unknown")
                print(f"Model: {model}")
                print(f"Serial: {serial}")

            # Get current SNMP community
            print(f"\nChecking current SNMP community...")
            current_community = get_snmp_community(client)

            if current_community is None:
                print(f"✗ Failed to get current SNMP community")
                results["connection_failed"].append(host)
                return False

            print(f"Current value: {'*' * len(current_community)} (masked)")
            print(f"Desired value: {'*' * len(desired_community)} (masked)")

            # Check if already correct
            if current_community == desired_community:
                print(f"✓ Already correct - no update needed")
                results["already_correct"].append(host)
                return True

            # Update the community string
            print(f"\nUpdating SNMP community...")
            if not set_snmp_community(client, desired_community):
                print(f"✗ Failed to update SNMP community")
                results["update_failed"].append(host)
                return False

            # Verify the update
            print(f"\nVerifying update...")
            current_community = get_snmp_community(client)

            if current_community == desired_community:
                print(f"✓ Verified - SNMP community successfully updated")
                results["updated_successfully"].append(host)
                return True
            else:
                print(f"✗ Verification failed - value did not change or is incorrect")
                results["verification_failed"].append(host)
                return False

    except Exception as e:
        print(f"✗ Error: {e}")
        results["connection_failed"].append(host)
        return False


def print_report():
    """Print a detailed report of the operation results."""
    total_processed = sum(len(hosts) for hosts in results.values())

    print(f"\n{'='*70}")
    print(f"SNMP COMMUNITY UPDATE REPORT")
    print(f"{'='*70}")
    print(f"Total hosts processed: {total_processed}")
    print()

    # Already correct
    if results["already_correct"]:
        print(f"✓ Already correct ({len(results['already_correct'])} hosts):")
        for host in results["already_correct"]:
            print(f"  - {host}")
        print()

    # Successfully updated
    if results["updated_successfully"]:
        print(f"✓ Successfully updated ({len(results['updated_successfully'])} hosts):")
        for host in results["updated_successfully"]:
            print(f"  - {host}")
        print()

    # Update failed
    if results["update_failed"]:
        print(f"✗ Update failed ({len(results['update_failed'])} hosts):")
        for host in results["update_failed"]:
            print(f"  - {host}")
        print()

    # Verification failed
    if results["verification_failed"]:
        print(f"⚠️  Verification failed ({len(results['verification_failed'])} hosts):")
        for host in results["verification_failed"]:
            print(f"  - {host}")
        print()

    # Connection failed
    if results["connection_failed"]:
        print(f"✗ Connection failed ({len(results['connection_failed'])} hosts):")
        for host in results["connection_failed"]:
            print(f"  - {host}")
        print()

    # Summary
    success_count = len(results["already_correct"]) + len(
        results["updated_successfully"]
    )
    fail_count = (
        len(results["update_failed"])
        + len(results["verification_failed"])
        + len(results["connection_failed"])
    )

    print(f"{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"✓ Success: {success_count} (all hosts now have correct SNMP community)")
    print(f"  - Already correct     : {len(results['already_correct'])}")
    print(f"  - Updated successfully: {len(results['updated_successfully'])}")
    print()
    print(f"✗ Failed: {fail_count}")
    print(f"  - Update failed.     : {len(results['update_failed'])}")
    print(f"  - Verification failed: {len(results['verification_failed'])}")
    print(f"  - Connection failed. : {len(results['connection_failed'])}")
    print(f"{'='*70}")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Set SNMP community string on iDRAC servers using gold file pattern",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script implements the gold file pattern for safe, auditable operations:

1. The gold file remains untouched (immutable)
2. A timestamped working copy is created automatically
3. SNMP community string is read from .env file (secure)
4. Each iDRAC is checked:
   - If already correct, marked as success
   - If different, updated and verified
   - Only removed from list if correct value is confirmed
5. Detailed report generated at the end

Security:
  - SNMP community string must be in .env file (SNMP_COMMUNITY=value)
  - Never exposed on command line or in logs
  - Working copies show audit trail of operations

Example .env:
  IDRAC_USERNAME=root
  IDRAC_PASSWORD=your_password
  SNMP_COMMUNITY=YourSecureCommunity

Usage Examples:
  # Process all hosts in gold file
  %(prog)s hosts-gold.txt

  # Use custom work directory
  %(prog)s hosts-gold.txt --work-dir ./snmp-runs

  # Dry run mode (check only, no updates)
  %(prog)s hosts-gold.txt --dry-run

  # Keep working copy even on full success
  %(prog)s hosts-gold.txt --keep-working-copy
        """,
    )

    parser.add_argument("gold_file", help="Path to immutable gold standard host file")
    parser.add_argument(
        "--work-dir",
        default="./work",
        help="Directory for timestamped working copies (default: ./work)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check current values only, do not update",
    )
    parser.add_argument(
        "--keep-working-copy",
        action="store_true",
        help="Keep working copy even if all hosts succeed",
    )
    parser.add_argument(
        "--stop-on-error", action="store_true", help="Stop processing on first error"
    )

    args = parser.parse_args()

    # Get SNMP community from environment
    snmp_community = os.getenv("SNMP_COMMUNITY")
    if not snmp_community:
        print("Error: SNMP_COMMUNITY not set in environment")
        print("Please add SNMP_COMMUNITY=your_community_string to .env file")
        return 1

    print(f"SNMP Community configured: {'*' * len(snmp_community)} (masked)")

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")

    # Verify gold file exists
    gold_path = Path(args.gold_file)
    if not gold_path.exists():
        print(f"Error: Gold file '{args.gold_file}' not found")
        print(f"\nCreate it with:")
        print(f"  python hostfile.py create {args.gold_file} YOUR_IDRAC_IP")
        return 1

    # Create timestamped working copy from gold file
    print(f"\n{'='*70}")
    print(f"Creating working copy from gold file...")
    print(f"{'='*70}")

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

    print(f"\n{'='*70}")
    print(f"Processing {initial_count} host(s) from working copy")
    print(f"{'='*70}")

    # Process all hosts
    def process_wrapper(host: str) -> bool:
        if args.dry_run:
            # In dry run, just check - don't update
            try:
                client = IDracClient(host)
                with client.get_session():
                    current = get_snmp_community(client)
                    if current == snmp_community:
                        print(f"✓ {host}: Already correct")
                        results["already_correct"].append(host)
                        return True
                    else:
                        print(f"⚠️  {host}: Would be updated")
                        results["update_failed"].append(host)
                        return False
            except Exception as e:
                print(f"✗ {host}: {e}")
                results["connection_failed"].append(host)
                return False
        else:
            return process_idrac(host, snmp_community)

    success_count, fail_count = hostfile.process_hosts(
        callback=process_wrapper,
        remove_on_success=not args.dry_run,  # Don't remove in dry run
        stop_on_error=args.stop_on_error,
    )

    # Print detailed report
    print_report()

    # Show file status
    remaining = hostfile.get_host_count()
    print(f"\nFile Status:")
    print(f"  Gold file: {args.gold_file} ({initial_count} hosts)")
    print(f"  Working copy: {working_file_path} ({remaining} hosts remaining)")

    # Clean up working copy if appropriate
    if not args.dry_run and remaining == 0 and not args.keep_working_copy:
        working_file_path.unlink()
        print(f"\n✓ All hosts successful - removed working copy")
    else:
        print(f"\n✓ Working copy preserved: {working_file_path}")
        if not args.keep_working_copy and remaining == 0:
            print(f"  (use --keep-working-copy to preserve even on full success)")

    # Return exit code
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
