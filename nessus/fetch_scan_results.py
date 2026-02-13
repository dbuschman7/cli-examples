#!/usr/bin/env python3
"""
Nessus Tenable Security Center API Client
Fetch scan results using username/password authentication
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from urllib3.exceptions import InsecureRequestWarning


class NessusSecurityCenterClient:
    """Client for Nessus Tenable Security Center REST API"""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        cert_file: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        """
        Initialize the Nessus Security Center client

        Args:
            base_url: Base URL of the Security Center (e.g., https://sc.example.com)
            username: Username for authentication
            password: Password for authentication
            cert_file: Path to custom CA certificate file for SSL verification
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token = None

        # Configure SSL verification
        if not verify_ssl:
            # Disable SSL warnings if verification is disabled
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
            self.session.verify = False
        elif cert_file:
            # Use custom certificate
            cert_path = Path(cert_file)
            if not cert_path.exists():
                raise FileNotFoundError(f"Certificate file not found: {cert_file}")
            self.session.verify = str(cert_path)
        else:
            # Use default SSL verification
            self.session.verify = True

        # Set default headers
        self.session.headers.update(
            {"Content-Type": "application/json", "Accept": "application/json"}
        )

    def login(self) -> Dict[str, Any]:
        """
        Authenticate with Security Center using username and password

        Returns:
            Response data containing token and user information

        Raises:
            requests.exceptions.RequestException: If login fails
        """
        url = f"{self.base_url}/rest/token"

        payload = {"username": self.username, "password": self.password}

        print(f"Logging in to {self.base_url}...")

        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()

            data = response.json()

            if data.get("error_code"):
                raise Exception(
                    f"Login failed: {data.get('error_msg', 'Unknown error')}"
                )

            # Extract token from response
            if "response" in data and "token" in data["response"]:
                self.token = data["response"]["token"]
                # Add token to session headers
                self.session.headers.update({"X-SecurityCenter": self.token})
                print(f"✓ Successfully logged in as {self.username}")
                return data["response"]
            else:
                raise Exception("No token found in login response")

        except requests.exceptions.RequestException as e:
            print(f"❌ Login failed: {e}")
            raise

    def logout(self):
        """
        Logout and invalidate the current token
        """
        if not self.token:
            return

        url = f"{self.base_url}/rest/token"

        try:
            response = self.session.delete(url)
            response.raise_for_status()
            print("✓ Logged out successfully")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Logout warning: {e}")
        finally:
            self.token = None
            if "X-SecurityCenter" in self.session.headers:
                del self.session.headers["X-SecurityCenter"]

    def get_scan(self, scan_id: int) -> Dict[str, Any]:
        """
        Get details of a specific scan

        Args:
            scan_id: The scan ID to retrieve

        Returns:
            Scan details
        """
        if not self.token:
            raise Exception("Not logged in. Call login() first.")

        url = f"{self.base_url}/rest/scan/{scan_id}"

        print(f"Fetching scan {scan_id}...")

        try:
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("error_code"):
                raise Exception(f"API error: {data.get('error_msg', 'Unknown error')}")

            return data.get("response", {})

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch scan {scan_id}: {e}")
            raise

    def get_scan_results(self, scan_id: int) -> Dict[str, Any]:
        """
        Get results of a specific scan

        Args:
            scan_id: The scan ID to retrieve results for

        Returns:
            Scan results
        """
        if not self.token:
            raise Exception("Not logged in. Call login() first.")

        url = f"{self.base_url}/rest/scanResult/{scan_id}"

        print(f"Fetching scan results for scan {scan_id}...")

        try:
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()

            if data.get("error_code"):
                raise Exception(f"API error: {data.get('error_msg', 'Unknown error')}")

            return data.get("response", {})

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch scan results {scan_id}: {e}")
            raise

    def download_scan_results(
        self, scan_result_id: int, output_file: str, result_type: str = "json"
    ) -> Path:
        """
        Download scan results to a file

        Args:
            scan_result_id: The scan result ID
            output_file: Path to output file
            result_type: Format type (json, csv, xml)

        Returns:
            Path to the downloaded file
        """
        if not self.token:
            raise Exception("Not logged in. Call login() first.")

        url = f"{self.base_url}/rest/scanResult/{scan_result_id}/download"

        params = {"type": result_type}

        print(f"Downloading scan result {scan_result_id} to {output_file}...")

        try:
            response = self.session.get(url, params=params, stream=True)
            response.raise_for_status()

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"✓ Downloaded to {output_path}")
            return output_path

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to download scan result {scan_result_id}: {e}")
            raise

    def get_multiple_scans(self, scan_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Get details for multiple scans

        Args:
            scan_ids: List of scan IDs to retrieve

        Returns:
            Dictionary mapping scan IDs to their details
        """
        results = {}

        for scan_id in scan_ids:
            try:
                scan_data = self.get_scan(scan_id)
                results[scan_id] = scan_data
            except Exception as e:
                print(f"⚠️  Warning: Could not fetch scan {scan_id}: {e}")
                results[scan_id] = {"error": str(e)}

        return results

    def get_multiple_scan_results(
        self, scan_ids: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get results for multiple scans

        Args:
            scan_ids: List of scan IDs to retrieve results for

        Returns:
            Dictionary mapping scan IDs to their results
        """
        results = {}

        for scan_id in scan_ids:
            try:
                scan_results = self.get_scan_results(scan_id)
                results[scan_id] = scan_results
            except Exception as e:
                print(f"⚠️  Warning: Could not fetch results for scan {scan_id}: {e}")
                results[scan_id] = {"error": str(e)}

        return results


def parse_scan_ids(scan_ids_str: str) -> List[int]:
    """
    Parse scan IDs from comma-separated string

    Args:
        scan_ids_str: Comma-separated scan IDs (e.g., "1,2,3")

    Returns:
        List of scan IDs as integers
    """
    try:
        return [int(sid.strip()) for sid in scan_ids_str.split(",")]
    except ValueError as e:
        raise ValueError(f"Invalid scan ID format: {e}")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Fetch scan results from Nessus Tenable Security Center",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch single scan
  %(prog)s -u https://sc.example.com -U admin -P password -s 123
  
  # Fetch multiple scans
  %(prog)s -u https://sc.example.com -U admin -P password -s 123,456,789
  
  # Use custom certificate
  %(prog)s -u https://sc.example.com -U admin -P password -s 123 --cert /path/to/cert.pem
  
  # Disable SSL verification (not recommended)
  %(prog)s -u https://sc.example.com -U admin -P password -s 123 --no-verify
  
  # Save results to file
  %(prog)s -u https://sc.example.com -U admin -P password -s 123 -o scan_results.json
        """,
    )

    # Required arguments
    parser.add_argument(
        "-u",
        "--url",
        required=True,
        help="Security Center base URL (e.g., https://sc.example.com)",
    )
    parser.add_argument(
        "-U", "--username", required=True, help="Username for authentication"
    )
    parser.add_argument(
        "-P", "--password", required=True, help="Password for authentication"
    )
    parser.add_argument(
        "-s",
        "--scans",
        required=True,
        help="Comma-separated list of scan IDs (e.g., 123,456,789)",
    )

    # Optional arguments
    parser.add_argument("-o", "--output", help="Output file path (JSON format)")
    parser.add_argument("--cert", help="Path to custom CA certificate file")
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Disable SSL certificate verification (not recommended)",
    )
    parser.add_argument(
        "--results-only",
        action="store_true",
        help="Fetch scan results instead of scan details",
    )

    args = parser.parse_args()

    # Parse scan IDs
    try:
        scan_ids = parse_scan_ids(args.scans)
        print(f"Fetching data for {len(scan_ids)} scan(s): {scan_ids}\n")
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    # Initialize client
    try:
        client = NessusSecurityCenterClient(
            base_url=args.url,
            username=args.username,
            password=args.password,
            cert_file=args.cert,
            verify_ssl=not args.no_verify,
        )
    except Exception as e:
        print(f"Error initializing client: {e}")
        return 1

    try:
        # Login
        client.login()
        print()

        # Fetch scan data
        if args.results_only:
            data = client.get_multiple_scan_results(scan_ids)
        else:
            data = client.get_multiple_scans(scan_ids)

        print(f"\n{'='*70}")
        print(f"Successfully fetched data for {len(data)} scan(s)")
        print(f"{'='*70}\n")

        # Display summary
        for scan_id, scan_data in data.items():
            if "error" in scan_data:
                print(f"Scan {scan_id}: ❌ {scan_data['error']}")
            else:
                scan_name = scan_data.get("name", "Unknown")
                status = scan_data.get("status", "Unknown")
                print(f"Scan {scan_id}: ✓ {scan_name} (Status: {status})")

        # Save to file if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)

            print(f"\n✓ Results saved to {output_path}")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        # Always logout
        client.logout()


if __name__ == "__main__":
    sys.exit(main())
