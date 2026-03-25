#!/usr/bin/env python3
"""
Dell iDRAC Redfish API Client

Provides session management and common operations for Dell iDRAC 9 via Redfish API.
Handles authentication, SSL verification, and session lifecycle.

Environment Variables:
    IDRAC_USERNAME: iDRAC username (default: root)
    IDRAC_PASSWORD: iDRAC password (required)
    IDRAC_VERIFY_CERT: SSL verification (true/false, default: false)
    CERT_PATH: Path to CA certificate bundle (optional)
"""

import os
import sys
import json
import requests
import urllib3
from typing import Optional, Dict, Any, Tuple
from contextlib import contextmanager
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Suppress insecure request warnings if SSL verification is disabled
if not os.getenv("IDRAC_VERIFY_CERT", "false").lower() == "true":
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IDracClient:
    """
    Dell iDRAC Redfish API client with session management.

    Features:
    - Automatic session creation and cleanup
    - SSL certificate verification (configurable)
    - Environment-based configuration
    - Context manager support for automatic cleanup
    - Common API operations
    """

    def __init__(
        self,
        host: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_cert: Optional[bool] = None,
        cert_path: Optional[str] = None,
    ):
        """
        Initialize iDRAC client.

        Args:
            host: iDRAC hostname or IP address
            username: iDRAC username (default: from IDRAC_USERNAME env)
            password: iDRAC password (default: from IDRAC_PASSWORD env)
            verify_cert: Verify SSL certificates (default: from IDRAC_VERIFY_CERT env)
            cert_path: Path to CA certificate bundle (default: from CERT_PATH env)
        """
        self.host = host
        self.username = username or os.getenv("IDRAC_USERNAME", "root")
        self.password = password or os.getenv("IDRAC_PASSWORD")

        if not self.password:
            raise ValueError(
                "iDRAC password is required. "
                "Set IDRAC_PASSWORD environment variable or pass password parameter."
            )

        # SSL verification configuration
        verify_env = os.getenv("IDRAC_VERIFY_CERT", "false").lower()
        self.verify_cert = (
            verify_cert if verify_cert is not None else (verify_env == "true")
        )

        # Certificate path
        self.cert_path = cert_path or os.getenv("CERT_PATH")
        if self.verify_cert and self.cert_path:
            self.verify = self.cert_path
        else:
            self.verify = self.verify_cert

        # Base URL for Redfish API
        self.base_url = f"https://{self.host}/redfish/v1"

        # Session management
        self.session = None
        self.session_id = None
        self.session_token = None

    def create_session(self) -> bool:
        """
        Create a Redfish session.

        Returns:
            True if session created successfully, False otherwise
        """
        if self.session:
            return True

        self.session = requests.Session()
        self.session.verify = self.verify

        # Create session via Redfish SessionService
        session_url = f"{self.base_url}/SessionService/Sessions"
        payload = {"UserName": self.username, "Password": self.password}

        try:
            response = self.session.post(
                session_url, json=payload, verify=self.verify, timeout=30
            )

            if response.status_code == 201:
                # Extract session token from headers
                self.session_token = response.headers.get("X-Auth-Token")

                # Extract session location from headers
                session_location = response.headers.get("Location")
                if session_location:
                    self.session_id = session_location.split("/")[-1]

                # Set token for future requests
                if self.session_token:
                    self.session.headers.update({"X-Auth-Token": self.session_token})

                return True
            else:
                print(f"Failed to create session: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Error creating session: {e}")
            return False

    def delete_session(self) -> bool:
        """
        Delete the current Redfish session.

        Returns:
            True if session deleted successfully, False otherwise
        """
        if not self.session or not self.session_id:
            return True

        session_url = f"{self.base_url}/SessionService/Sessions/{self.session_id}"

        try:
            response = self.session.delete(session_url, verify=self.verify, timeout=30)

            if response.status_code in [200, 204]:
                self.session_token = None
                self.session_id = None
                self.session = None
                return True
            else:
                print(f"Warning: Failed to delete session: HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"Warning: Error deleting session: {e}")
            return False

    @contextmanager
    def get_session(self):
        """
        Context manager for automatic session lifecycle management.

        Usage:
            with client.get_session():
                # Perform operations
                info = client.get_system_info()
        """
        try:
            if not self.create_session():
                raise Exception("Failed to create iDRAC session")
            yield self
        finally:
            self.delete_session()

    def get(self, path: str, **kwargs) -> requests.Response:
        """
        Perform GET request to iDRAC.

        Args:
            path: API path (relative to /redfish/v1)
            **kwargs: Additional arguments for requests.get()

        Returns:
            Response object
        """
        if not self.session:
            raise Exception("No active session. Call create_session() first.")

        url = f"{self.base_url}/{path.lstrip('/')}"
        return self.session.get(url, verify=self.verify, timeout=30, **kwargs)

    def post(
        self, path: str, data: Optional[Dict] = None, **kwargs
    ) -> requests.Response:
        """
        Perform POST request to iDRAC.

        Args:
            path: API path (relative to /redfish/v1)
            data: JSON data to send
            **kwargs: Additional arguments for requests.post()

        Returns:
            Response object
        """
        if not self.session:
            raise Exception("No active session. Call create_session() first.")

        url = f"{self.base_url}/{path.lstrip('/')}"
        return self.session.post(
            url, json=data, verify=self.verify, timeout=30, **kwargs
        )

    def patch(
        self, path: str, data: Optional[Dict] = None, **kwargs
    ) -> requests.Response:
        """
        Perform PATCH request to iDRAC.

        Args:
            path: API path (relative to /redfish/v1)
            data: JSON data to send
            **kwargs: Additional arguments for requests.patch()

        Returns:
            Response object
        """
        if not self.session:
            raise Exception("No active session. Call create_session() first.")

        url = f"{self.base_url}/{path.lstrip('/')}"
        return self.session.patch(
            url, json=data, verify=self.verify, timeout=30, **kwargs
        )

    def delete(self, path: str, **kwargs) -> requests.Response:
        """
        Perform DELETE request to iDRAC.

        Args:
            path: API path (relative to /redfish/v1)
            **kwargs: Additional arguments for requests.delete()

        Returns:
            Response object
        """
        if not self.session:
            raise Exception("No active session. Call create_session() first.")

        url = f"{self.base_url}/{path.lstrip('/')}"
        return self.session.delete(url, verify=self.verify, timeout=30, **kwargs)

    # Common convenience methods

    def get_system_info(self) -> Optional[Dict[str, Any]]:
        """
        Get basic system information.

        Returns:
            Dictionary with system information or None on error
        """
        try:
            response = self.get("/Systems/System.Embedded.1")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get system info: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting system info: {e}")
            return None

    def get_manager_info(self) -> Optional[Dict[str, Any]]:
        """
        Get iDRAC manager information.

        Returns:
            Dictionary with manager information or None on error
        """
        try:
            response = self.get("/Managers/iDRAC.Embedded.1")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get manager info: HTTP {response.status_code}")
                return None
        except Exception as e:
            print(f"Error getting manager info: {e}")
            return None

    def get_power_state(self) -> Optional[str]:
        """
        Get current power state of the system.

        Returns:
            Power state string (On, Off, etc.) or None on error
        """
        info = self.get_system_info()
        if info:
            return info.get("PowerState")
        return None

    def get_health_status(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get system health and status.

        Returns:
            Tuple of (health, state) or (None, None) on error
        """
        info = self.get_system_info()
        if info and "Status" in info:
            health = info["Status"].get("Health")
            state = info["Status"].get("State")
            return health, state
        return None, None

    def test_connection(self) -> bool:
        """
        Test connection to iDRAC and verify credentials.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_session():
                info = self.get_system_info()
                if info:
                    print(f"✓ Connected to iDRAC: {self.host}")
                    if "Manufacturer" in info:
                        print(f"  Manufacturer: {info['Manufacturer']}")
                    if "Model" in info:
                        print(f"  Model: {info['Model']}")
                    if "SerialNumber" in info:
                        print(f"  Serial: {info['SerialNumber']}")
                    if "PowerState" in info:
                        print(f"  Power State: {info['PowerState']}")
                    return True
                else:
                    print(f"✗ Failed to retrieve system info from {self.host}")
                    return False
        except Exception as e:
            print(f"✗ Connection failed to {self.host}: {e}")
            return False


def main():
    """Test iDRAC connection with environment configuration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test iDRAC Redfish API connection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  IDRAC_USERNAME        iDRAC username (default: root)
  IDRAC_PASSWORD        iDRAC password (required)
  IDRAC_VERIFY_CERT     Verify SSL certificates (true/false)
  CERT_PATH             Path to CA certificate bundle

Examples:
  # Test connection to a single iDRAC
  %(prog)s 192.168.1.100
  
  # Test with explicit credentials
  %(prog)s 192.168.1.100 --username root --password calvin
  
  # Test multiple hosts
  %(prog)s 192.168.1.100 192.168.1.101 192.168.1.102
        """,
    )

    parser.add_argument("hosts", nargs="+", help="iDRAC hostname(s) or IP address(es)")
    parser.add_argument("--username", help="iDRAC username (overrides IDRAC_USERNAME)")
    parser.add_argument("--password", help="iDRAC password (overrides IDRAC_PASSWORD)")
    parser.add_argument(
        "--verify-cert", action="store_true", help="Enable SSL certificate verification"
    )
    parser.add_argument("--cert-path", help="Path to CA certificate bundle")

    args = parser.parse_args()

    # Test each host
    success_count = 0
    fail_count = 0

    for host in args.hosts:
        print(f"\n{'='*60}")
        print(f"Testing: {host}")
        print(f"{'='*60}")

        try:
            client = IDracClient(
                host=host,
                username=args.username,
                password=args.password,
                verify_cert=args.verify_cert if args.verify_cert else None,
                cert_path=args.cert_path,
            )

            if client.test_connection():
                success_count += 1
            else:
                fail_count += 1

        except Exception as e:
            print(f"✗ Error: {e}")
            fail_count += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary: {success_count} succeeded, {fail_count} failed")
    print(f"{'='*60}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
