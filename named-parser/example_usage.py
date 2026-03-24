#!/usr/bin/env python3
"""
Example script demonstrating how to use the DNS Zone Parser.

This script shows how to:
1. Parse multiple zone files
2. Analyze the results
3. Query specific record types
4. Identify CNAMEs vs base hostnames
"""

from zone_parser import DNSZoneParser
import pandas as pd


def main():
    print("=" * 70)
    print("DNS Zone File Parser - Example Usage")
    print("=" * 70)

    # Initialize parser
    parser = DNSZoneParser()

    # List of zone files to parse
    zone_files = [
        "example-forward.zone",
        "example-reverse.zone",
        "example-reverse-dmz.zone",
    ]

    # Parse all zone files
    df = parser.parse_and_save(zone_files, output_file="example_output.parquet")

    print("\n" + "=" * 70)
    print("ANALYSIS OF PARSED RECORDS")
    print("=" * 70)

    # 1. Show all base hostnames (A records)
    print("\n1. Base Hostnames (A records):")
    print("-" * 70)
    a_records = df[df["type"] == "A"][["hostname", "ip"]]
    print(a_records.to_string(index=False))

    # 2. Show all CNAMEs (aliases)
    print("\n2. CNAME Records (Aliases):")
    print("-" * 70)
    cnames = df[df["is_cname"] == True][["hostname", "canonical_name"]]
    if not cnames.empty:
        print(cnames.to_string(index=False))
    else:
        print("No CNAME records found")

    # 3. Show PTR records (reverse lookups)
    print("\n3. PTR Records (Reverse Lookups):")
    print("-" * 70)
    ptr_records = df[df["type"] == "PTR"][["ip", "hostname"]]
    if not ptr_records.empty:
        print(ptr_records.to_string(index=False))
    else:
        print("No PTR records found")

    # 4. Check for hosts with both forward and reverse DNS
    print("\n4. Forward/Reverse DNS Consistency Check:")
    print("-" * 70)

    # Get hostnames from A records
    forward_hosts = set(df[df["type"] == "A"]["hostname"])

    # Get hostnames from PTR records
    reverse_hosts = set(df[df["type"] == "PTR"]["hostname"])

    # Find hosts with both
    both = forward_hosts & reverse_hosts
    print(f"Hosts with forward records: {len(forward_hosts)}")
    print(f"Hosts with reverse records: {len(reverse_hosts)}")
    print(f"Hosts with BOTH forward and reverse: {len(both)}")

    # Find hosts missing reverse DNS
    missing_reverse = forward_hosts - reverse_hosts
    if missing_reverse:
        print(f"\nWarning: {len(missing_reverse)} hosts missing reverse DNS:")
        for host in sorted(missing_reverse):
            ip = df[(df["type"] == "A") & (df["hostname"] == host)]["ip"].values
            if len(ip) > 0:
                print(f"  - {host} ({ip[0]})")

    # 5. Show MX records
    print("\n5. MX Records (Mail Exchangers):")
    print("-" * 70)
    mx_records = df[df["type"] == "MX"][["hostname", "priority", "value"]]
    if not mx_records.empty:
        print(mx_records.to_string(index=False))
    else:
        print("No MX records found")

    # 6. Summary statistics
    print("\n6. Summary Statistics:")
    print("-" * 70)
    print(f"Total records parsed: {len(df)}")
    print(f"  A records: {len(df[df['type'] == 'A'])}")
    print(f"  CNAME records: {len(df[df['type'] == 'CNAME'])}")
    print(f"  PTR records: {len(df[df['type'] == 'PTR'])}")
    print(f"  MX records: {len(df[df['type'] == 'MX'])}")
    print(f"  NS records: {len(df[df['type'] == 'NS'])}")
    print(
        f"  Other records: {len(df[~df['type'].isin(['A', 'CNAME', 'PTR', 'MX', 'NS'])])}"
    )

    # 7. Show IP address distribution
    print("\n7. IP Address Distribution:")
    print("-" * 70)
    ips_with_records = df[df["ip"].notna()]
    if not ips_with_records.empty:
        # Group by subnet
        def get_subnet(ip):
            if pd.isna(ip):
                return None
            parts = str(ip).split(".")
            if len(parts) >= 3:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
            return str(ip)

        ips_with_records["subnet"] = ips_with_records["ip"].apply(get_subnet)
        subnet_counts = ips_with_records["subnet"].value_counts()
        print(subnet_counts.to_string())

    print("\n" + "=" * 70)
    print(f"Results saved to: example_output.parquet")
    print("=" * 70)

    # Show how to load the parquet file later
    print("\nTo load this data later:")
    print("  import pandas as pd")
    print("  df = pd.read_parquet('example_output.parquet')")


if __name__ == "__main__":
    main()
