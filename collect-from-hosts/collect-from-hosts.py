#!/usr/bin/env python3
"""
Collect information from multiple hosts via SSH concurrently.
Provides a base class for executing commands and parsing responses.
"""

import os
import argparse
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from abc import ABC, abstractmethod

# Ignore warnings from paramiko about weak ciphers
import warnings
warnings.filterwarnings(action="ignore", module=".*paramiko.*")
import paramiko


class SSHConnection:
    """Manages persistent SSH connection to a remote host."""

    def __init__(
        self,
        host: str,
        username: Optional[str] = None,
        identity_file: Optional[str] = None,
        debug: bool = False,
    ):
        """Initialize SSH connection to remote host.

        Args:
            host: Hostname (user@host format supported)
            username: SSH username (overrides user in host string)
            identity_file: Path to SSH key file
            debug: Enable debug logging
        """
        self.host = host  # Original hostname
        self.username = username
        self.identity_file = identity_file
        self.debug = debug
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Load SSH config
        self.ssh_config = paramiko.SSHConfig()
        try:
            with open(os.path.expanduser("~/.ssh/config")) as f:
                self.ssh_config.parse(f)
        except FileNotFoundError:
            pass  # No SSH config file

        self.connected = False

        # Set up logging if debug is enabled
        if self.debug:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            paramiko.util.log_to_file("/tmp/paramiko.log")
            self.logger = logging.getLogger(f"SSHConnection-{host}")
        else:
            self.logger = logging.getLogger(f"SSHConnection-{host}")
            self.logger.setLevel(logging.WARNING)

    def connect(self) -> None:
        """Establish SSH connection."""
        if self.debug:
            self.logger.debug(f"Starting SSH connection to {self.host}")

        # Parse username from host if in user@host format
        connect_host = self.host
        if "@" in self.host:
            parts = self.host.split("@", 1)
            if self.username is None:
                self.username = parts[0]
            connect_host = parts[1]

        # Apply SSH config for this host
        host_config = self.ssh_config.lookup(connect_host)

        # Get hostname from config (may be different from connect_host)
        hostname = host_config.get("hostname", connect_host)

        # Get username from config if not specified
        if self.username is None:
            self.username = host_config.get("user", os.getenv("USER"))

        # Get identity file from config if not specified
        if self.identity_file is None and "identityfile" in host_config:
            # identityfile can be a list
            identity_files = host_config["identityfile"]
            if isinstance(identity_files, list) and identity_files:
                self.identity_file = os.path.expanduser(identity_files[0])
            elif isinstance(identity_files, str):
                self.identity_file = os.path.expanduser(identity_files)

        if self.debug:
            self.logger.debug(
                f"Username: {self.username}, Hostname: {hostname}, Identity: {self.identity_file}"
            )

        # Configure connection parameters
        connect_kwargs = {
            "hostname": hostname,
            "username": self.username,
            "timeout": 10,
        }

        # Add identity file if specified
        if self.identity_file:
            connect_kwargs["key_filename"] = self.identity_file
            if self.debug:
                self.logger.debug(f"Using identity file: {self.identity_file}")

        if self.debug:
            self.logger.debug(f"Connecting with parameters: {connect_kwargs}")

        # Connect to remote host
        self.ssh.connect(**connect_kwargs)
        self.connected = True

        if self.debug:
            self.logger.debug("SSH connection established successfully")

    def execute_command(self, command: str, timeout: int = 30) -> tuple[str, str, int]:
        """Execute a command and return stdout, stderr, and exit code.
        
        Args:
            command: The command to execute
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        if not self.connected:
            raise RuntimeError("Not connected to host")

        try:
            if self.debug:
                self.logger.debug(f"Executing command: {command}")

            stdin, stdout, stderr = self.ssh.exec_command(command, timeout=timeout)

            # Wait for command to complete and read output
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode("utf-8")
            stderr_text = stderr.read().decode("utf-8")

            if self.debug:
                self.logger.debug(
                    f"Command completed with exit code {exit_code}, "
                    f"stdout: {len(stdout_text)} bytes, stderr: {len(stderr_text)} bytes"
                )

            return stdout_text, stderr_text, exit_code

        except Exception as e:
            if self.debug:
                self.logger.error(f"Error executing command: {e}")
            raise

    def close(self) -> None:
        """Close SSH connection."""
        if self.ssh:
            self.ssh.close()
        self.connected = False
        if self.debug:
            self.logger.debug("SSH connection closed")


class CommandExecutor(ABC):
    """Abstract base class for executing commands on remote hosts and parsing responses."""

    def __init__(self, host: str, username: Optional[str] = None, 
                 identity_file: Optional[str] = None, debug: bool = False):
        """Initialize the command executor.
        
        Args:
            host: Hostname to connect to
            username: SSH username
            identity_file: Path to SSH identity file
            debug: Enable debug logging
        """
        self.host = host
        self.connection = SSHConnection(host, username, identity_file, debug)
        self.debug = debug

    def connect(self) -> None:
        """Establish SSH connection to the host."""
        self.connection.connect()

    def close(self) -> None:
        """Close the SSH connection."""
        self.connection.close()

    @abstractmethod
    def get_commands(self) -> List[str]:
        """Return list of commands to execute on the remote host.
        
        Returns:
            List of shell commands to execute
        """
        pass

    @abstractmethod
    def parse_response(self, command: str, stdout: str, stderr: str, 
                      exit_code: int) -> Dict[str, Any]:
        """Parse the response from a command execution.
        
        Args:
            command: The command that was executed
            stdout: Standard output from the command
            stderr: Standard error from the command
            exit_code: Exit code from the command
            
        Returns:
            Dictionary with parsed data
        """
        pass

    def execute(self) -> Dict[str, Any]:
        """Execute all commands and return parsed results.
        
        Returns:
            Dictionary with results from all commands
        """
        results = {
            "host": self.host,
            "success": True,
            "error": None,
            "commands": {}
        }

        try:
            self.connect()
            
            for command in self.get_commands():
                try:
                    stdout, stderr, exit_code = self.connection.execute_command(command)
                    parsed = self.parse_response(command, stdout, stderr, exit_code)
                    results["commands"][command] = {
                        "exit_code": exit_code,
                        "parsed_data": parsed,
                        "success": exit_code == 0
                    }
                except Exception as e:
                    results["commands"][command] = {
                        "exit_code": -1,
                        "error": str(e),
                        "success": False
                    }
                    if self.debug:
                        print(f"Error executing '{command}' on {self.host}: {e}")
            
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            if self.debug:
                print(f"Failed to connect to {self.host}: {e}")
        finally:
            self.close()

        return results


def read_hosts_file(filepath: str) -> List[str]:
    """Read a file containing hostnames (one per line) and return list of hosts.
    
    Args:
        filepath: Path to the hosts file
        
    Returns:
        List of hostnames (empty lines and comments starting with # are ignored)
    """
    hosts = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                hosts.append(line)
    return hosts


def execute_on_hosts(executor_class: type, hosts: List[str], 
                     username: Optional[str] = None,
                     identity_file: Optional[str] = None,
                     max_workers: int = 10,
                     debug: bool = False) -> List[Dict[str, Any]]:
    """Execute commands on multiple hosts concurrently.
    
    Args:
        executor_class: Class derived from CommandExecutor to use
        hosts: List of hostnames to connect to
        username: SSH username (optional)
        identity_file: Path to SSH identity file (optional)
        max_workers: Maximum number of concurrent connections
        debug: Enable debug logging
        
    Returns:
        List of result dictionaries, one per host
    """
    results = []
    
    def execute_on_host(host: str) -> Dict[str, Any]:
        """Execute on a single host."""
        executor = executor_class(host, username, identity_file, debug)
        return executor.execute()
    
    # Execute concurrently on all hosts
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(execute_on_host, host): host for host in hosts}
        for future in as_completed(futures):
            host = futures[future]
            try:
                result = future.result()
                results.append(result)
                if debug:
                    print(f"Completed execution on {host}")
            except Exception as e:
                results.append({
                    "host": host,
                    "success": False,
                    "error": str(e),
                    "commands": {}
                })
                if debug:
                    print(f"Failed execution on {host}: {e}")
    
    return results


# Example implementation
class ExampleExecutor(CommandExecutor):
    """Example implementation that collects system information."""
    
    def get_commands(self) -> List[str]:
        """Return commands to collect system info."""
        return [
            "hostname",
            "uname -a",
            "uptime",
        ]
    
    def parse_response(self, command: str, stdout: str, stderr: str, 
                      exit_code: int) -> Dict[str, Any]:
        """Parse command responses into structured data."""
        return {
            "command": command,
            "output": stdout.strip(),
            "error": stderr.strip() if stderr else None,
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Execute commands on multiple hosts via SSH concurrently",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-f", "--hosts-file",
        type=str,
        required=True,
        help="File containing list of hostnames (one per line)"
    )
    parser.add_argument(
        "-u", "--username",
        type=str,
        help="SSH username (if not specified in hostname as user@host)"
    )
    parser.add_argument(
        "--identity-file",
        type=str,
        help="SSH identity file (private key) path. Can also be set via SSH_IDENTITY_FILE env var"
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=10,
        help="Maximum number of concurrent SSH connections"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Get identity file from command line or environment variable
    identity_file = args.identity_file or os.environ.get("SSH_IDENTITY_FILE")

    # Read hosts from file
    try:
        hosts = read_hosts_file(args.hosts_file)
        print(f"Read {len(hosts)} hosts from {args.hosts_file}")
    except FileNotFoundError:
        print(f"Error: Hosts file '{args.hosts_file}' not found")
        return 1
    except Exception as e:
        print(f"Error reading hosts file: {e}")
        return 1

    if not hosts:
        print("Error: No hosts found in file")
        return 1

    # Execute on all hosts using the example executor
    print(f"Executing commands on {len(hosts)} hosts...")
    results = execute_on_hosts(
        ExampleExecutor,
        hosts,
        username=args.username,
        identity_file=identity_file,
        max_workers=args.workers,
        debug=args.debug
    )

    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    for result in results:
        host = result["host"]
        success = result["success"]
        
        print(f"\n{host}: {'SUCCESS' if success else 'FAILED'}")
        if not success:
            print(f"  Error: {result.get('error', 'Unknown error')}")
        else:
            for cmd, cmd_result in result["commands"].items():
                if cmd_result["success"]:
                    parsed = cmd_result["parsed_data"]
                    print(f"  {cmd}: {parsed['output'][:100]}")
                else:
                    print(f"  {cmd}: FAILED - {cmd_result.get('error', 'Unknown error')}")

    # Summary
    successful = sum(1 for r in results if r["success"])
    print(f"\n{'='*80}")
    print(f"Summary: {successful}/{len(results)} hosts successful")
    
    return 0 if successful == len(results) else 1


if __name__ == "__main__":
    exit(main())
