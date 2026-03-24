#!/usr/bin/env python3
"""
DNS Zone File Parser using pyparsing

Parses BIND-style forward and reverse zone files, including:
- A records (hostname -> IP)
- CNAME records (alias -> canonical)
- PTR records (IP -> hostname)
- Comments and directives

Outputs a pandas DataFrame with all DNS records.
"""

from pyparsing import (
    Word,
    alphanums,
    alphas,
    nums,
    Literal,
    Optional,
    Group,
    Suppress,
    Regex,
    LineEnd,
    pythonStyleComment,
    OneOrMore,
    ZeroOrMore,
    CaselessLiteral,
    ParseException,
    restOfLine,
    Combine,
    White,
    delimitedList,
)
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import re


class DNSZoneParser:
    """Parser for DNS zone files using pyparsing."""

    def __init__(self):
        self.records = []
        self.current_origin = ""
        self.current_ttl = 86400  # Default TTL
        self._setup_grammar()

    def _setup_grammar(self):
        """Define the pyparsing grammar for DNS zone files."""

        # Basic tokens
        comment = Literal(";") + restOfLine

        # Domain name - allow dots, hyphens, underscores, alphanumerics
        domain_label = Word(alphanums + "-_")
        domain = Combine(
            domain_label
            + ZeroOrMore(Literal(".") + domain_label)
            + Optional(Literal("."))
        )

        # Special tokens
        at_sign = Literal("@")
        hostname = domain | at_sign | Word(alphanums + "-_.*")

        # IPv4 address
        ipv4_octet = Word(nums, min=1, max=3)
        ipv4 = Combine(
            ipv4_octet + "." + ipv4_octet + "." + ipv4_octet + "." + ipv4_octet
        )

        # TTL (time to live) - optional
        ttl = Word(nums)

        # Class (IN, CH, HS) - usually IN for Internet
        record_class = (
            CaselessLiteral("IN") | CaselessLiteral("CH") | CaselessLiteral("HS")
        )

        # Record types
        record_type = (
            CaselessLiteral("A")
            | CaselessLiteral("AAAA")
            | CaselessLiteral("CNAME")
            | CaselessLiteral("PTR")
            | CaselessLiteral("MX")
            | CaselessLiteral("NS")
            | CaselessLiteral("TXT")
            | CaselessLiteral("SOA")
            | CaselessLiteral("SRV")
        )

        # A Record: hostname [TTL] [class] A ipv4
        a_record = (
            hostname("name")
            + Optional(ttl)("ttl")
            + Optional(record_class)("class")
            + CaselessLiteral("A")("type")
            + ipv4("value")
        )

        # CNAME Record: alias [TTL] [class] CNAME canonical
        cname_record = (
            hostname("name")
            + Optional(ttl)("ttl")
            + Optional(record_class)("class")
            + CaselessLiteral("CNAME")("type")
            + hostname("value")
        )

        # PTR Record: ip-reverse [TTL] [class] PTR hostname
        ptr_record = (
            hostname("name")
            + Optional(ttl)("ttl")
            + Optional(record_class)("class")
            + CaselessLiteral("PTR")("type")
            + hostname("value")
        )

        # MX Record: hostname [TTL] [class] MX priority mailserver
        mx_record = (
            hostname("name")
            + Optional(ttl)("ttl")
            + Optional(record_class)("class")
            + CaselessLiteral("MX")("type")
            + Word(nums)("priority")
            + hostname("value")
        )

        # NS Record: hostname [TTL] [class] NS nameserver
        ns_record = (
            hostname("name")
            + Optional(ttl)("ttl")
            + Optional(record_class)("class")
            + CaselessLiteral("NS")("type")
            + hostname("value")
        )

        # SOA Record (simplified - we'll skip the details)
        soa_start = (
            hostname + Optional(ttl) + Optional(record_class) + CaselessLiteral("SOA")
        )

        # TXT Record
        txt_value = Regex(r'"[^"]*"') | Word(alphanums + "-_./:")
        txt_record = (
            hostname("name")
            + Optional(ttl)("ttl")
            + Optional(record_class)("class")
            + CaselessLiteral("TXT")("type")
            + txt_value("value")
        )

        # Directives
        origin_directive = Literal("$ORIGIN") + domain("origin")
        ttl_directive = Literal("$TTL") + Word(nums)("default_ttl")

        # Main record grammar
        self.dns_record = (
            a_record | cname_record | ptr_record | mx_record | ns_record | txt_record
        )

        self.origin_directive = origin_directive
        self.ttl_directive = ttl_directive
        self.soa_start = soa_start

        # Ignore comments
        self.dns_record.ignore(comment)
        self.origin_directive.ignore(comment)
        self.ttl_directive.ignore(comment)

    def parse_zone_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Parse a DNS zone file and return a list of record dictionaries.

        Args:
            filepath: Path to the zone file

        Returns:
            List of dictionaries containing parsed DNS records
        """
        self.records = []
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Zone file not found: {filepath}")

        with open(filepath, "r") as f:
            lines = f.readlines()

        in_soa = False
        soa_paren_count = 0

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines
            if not line or line.startswith(";"):
                continue

            # Handle SOA records (skip them as they're complex)
            if "SOA" in line.upper():
                in_soa = True
                soa_paren_count = line.count("(") - line.count(")")
                continue

            if in_soa:
                soa_paren_count += line.count("(") - line.count(")")
                if soa_paren_count <= 0:
                    in_soa = False
                continue

            # Try to parse directives
            try:
                result = self.origin_directive.parseString(line)
                self.current_origin = result.origin
                continue
            except ParseException:
                pass

            try:
                result = self.ttl_directive.parseString(line)
                self.current_ttl = int(result.default_ttl)
                continue
            except ParseException:
                pass

            # Try to parse DNS records
            try:
                result = self.dns_record.parseString(line)
                record = self._extract_record(result)
                if record:
                    self.records.append(record)
            except ParseException as e:
                # Some lines might not match our patterns (like $INCLUDE, etc.)
                # We'll just skip them with a debug message
                # print(f"Line {line_num}: Could not parse: {line[:50]}...")
                pass

        return self.records

    def _extract_record(self, parsed_result) -> Dict[str, Any]:
        """Extract record information from parsed result."""
        record = {
            "name": parsed_result.name if parsed_result.name else "",
            "ttl": int(parsed_result.ttl) if parsed_result.ttl else self.current_ttl,
            "class": parsed_result.get("class", "IN"),
            "type": parsed_result.type.upper(),
            "value": parsed_result.value if parsed_result.value else "",
            "priority": (
                int(parsed_result.priority) if "priority" in parsed_result else None
            ),
        }

        # Handle @ symbol (means current origin)
        if record["name"] == "@":
            record["name"] = self.current_origin

        # Add origin to relative names (names not ending with .)
        if record["name"] and not record["name"].endswith(".") and self.current_origin:
            if record["name"]:
                record["name"] = f"{record['name']}.{self.current_origin}"
            else:
                record["name"] = self.current_origin

        return record

    def build_dataframe(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Build a pandas DataFrame from parsed records.

        The DataFrame includes:
        - ip: IP address (from A records or derived from PTR)
        - hostname: The hostname
        - record_type: A, CNAME, PTR, etc.
        - is_cname: Boolean indicating if this is a CNAME
        - canonical_name: For CNAMEs, the target hostname
        - ttl: Time to live
        """
        rows = []

        for record in records:
            row = {
                "name": record["name"],
                "type": record["type"],
                "value": record["value"],
                "ttl": record["ttl"],
                "priority": record.get("priority"),
            }

            # For A records
            if record["type"] == "A":
                row["ip"] = record["value"]
                row["hostname"] = record["name"]
                row["is_cname"] = False
                row["canonical_name"] = None

            # For CNAME records
            elif record["type"] == "CNAME":
                row["ip"] = None
                row["hostname"] = record["name"]  # This is the alias
                row["is_cname"] = True
                row["canonical_name"] = record["value"]  # This is the canonical name

            # For PTR records
            elif record["type"] == "PTR":
                # Reconstruct IP from reverse notation
                row["ip"] = self._reverse_to_ip(record["name"])
                row["hostname"] = record["value"]
                row["is_cname"] = False
                row["canonical_name"] = None

            # For other records (MX, NS, etc.)
            else:
                row["ip"] = None
                row["hostname"] = record["name"]
                row["is_cname"] = False
                row["canonical_name"] = None

            rows.append(row)

        df = pd.DataFrame(rows)

        # Reorder columns for clarity
        column_order = [
            "hostname",
            "ip",
            "type",
            "is_cname",
            "canonical_name",
            "value",
            "ttl",
            "priority",
            "name",
        ]
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]

        return df

    def _reverse_to_ip(self, reverse_name: str) -> str:
        """
        Convert reverse DNS notation to IP address.

        Example: 4.3.2.1.in-addr.arpa. -> 1.2.3.4
        """
        # Remove .in-addr.arpa. or .ip6.arpa. suffix
        parts = (
            reverse_name.replace(".in-addr.arpa.", "")
            .replace(".in-addr.arpa", "")
            .split(".")
        )

        # Reverse the parts to get IP
        try:
            if len(parts) >= 4:
                return ".".join(reversed(parts[:4]))
            else:
                # Partial reverse zone (e.g., /24)
                return ".".join(reversed(parts))
        except:
            return reverse_name

    def parse_and_save(
        self, zone_files: List[str], output_file: str = "dns_records.parquet"
    ):
        """
        Parse multiple zone files and save to a single parquet file.

        Args:
            zone_files: List of paths to zone files
            output_file: Output parquet file path
        """
        all_records = []

        for zone_file in zone_files:
            print(f"Parsing {zone_file}...")
            records = self.parse_zone_file(zone_file)
            all_records.extend(records)

        df = self.build_dataframe(all_records)

        print(f"\nParsed {len(df)} total records.")
        print(f"\nRecord type counts:")
        print(df["type"].value_counts())

        # Save to parquet
        df.to_parquet(output_file, index=False)
        print(f"\nSaved to {output_file}")

        return df


def main():
    """Example usage."""
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python zone_parser.py <zone_file1> [zone_file2 ...] [-o output.parquet]"
        )
        print("\nExample:")
        print(
            "  python zone_parser.py forward.zone reverse.zone -o dns_records.parquet"
        )
        sys.exit(1)

    # Parse arguments
    zone_files = []
    output_file = "dns_records.parquet"

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "-o" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        else:
            zone_files.append(sys.argv[i])
            i += 1

    if not zone_files:
        print("Error: No zone files specified")
        sys.exit(1)

    # Parse and save
    parser = DNSZoneParser()
    df = parser.parse_and_save(zone_files, output_file)

    # Display summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nTotal records: {len(df)}")
    print(f"\nA records: {len(df[df['type'] == 'A'])}")
    print(f"CNAME records: {len(df[df['type'] == 'CNAME'])}")
    print(f"PTR records: {len(df[df['type'] == 'PTR'])}")

    print("\nSample records:")
    print(df.head(10).to_string())


if __name__ == "__main__":
    main()
