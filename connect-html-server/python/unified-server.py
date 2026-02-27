#!/usr/bin/env /usr/bin/python3
"""
Unified server business logic handler.
Processes dynamic HTTP requests from Redpanda Connect.
"""

import sys
import json
from datetime import datetime
from pathlib import Path


def handle_request(request_data):
    """
    Handle incoming HTTP request and return response.

    Args:
        request_data: Dict with method, path, headers, body

    Returns:
        Dict: Response data
    """
    method = request_data.get("method", "GET")
    path = request_data.get("path", "/")
    body = request_data.get("body", "")

    # Parse body if it's JSON
    try:
        body_data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        body_data = {"raw": body}

    # Route based on path
    if path.startswith("/api/"):
        return handle_api_request(method, path, body_data)
    elif path == "/upload":
        return handle_upload(method, body_data)
    else:
        return handle_default(method, path, body_data)


def handle_api_request(method, path, data):
    """Handle API requests."""
    api_path = path.replace("/api/", "")

    return {
        "status": "success",
        "method": method,
        "endpoint": api_path,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": f"API endpoint '{api_path}' processed successfully",
    }


def handle_upload(method, data):
    """Handle file upload requests."""
    if method != "POST":
        return {
            "status": "error",
            "message": "Upload endpoint only accepts POST requests",
        }

    return {
        "status": "success",
        "message": "Upload processed",
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def handle_default(method, path, data):
    """Handle default/catch-all requests."""
    return {
        "status": "success",
        "method": method,
        "path": path,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "Request processed by Python backend",
    }


def main():
    """Main entry point - reads from stdin, processes, writes to stdout."""
    try:
        # Read request data from stdin
        input_data = sys.stdin.read()

        if not input_data:
            response = {"status": "error", "message": "No input data"}
        else:
            request_data = json.loads(input_data)
            response = handle_request(request_data)

        # Write response to stdout
        print(json.dumps(response))
        sys.stdout.flush()

    except json.JSONDecodeError as e:
        error_response = {"status": "error", "message": f"Invalid JSON input: {str(e)}"}
        print(json.dumps(error_response))
        sys.exit(1)

    except Exception as e:
        error_response = {"status": "error", "message": f"Processing error: {str(e)}"}
        print(json.dumps(error_response))
        sys.exit(1)


if __name__ == "__main__":
    main()
