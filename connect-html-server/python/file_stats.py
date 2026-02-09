#!/usr/bin/env python3
"""
File statistics processor that scans an upload directory,
processes files, moves them to processed directory, and logs results.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import shutil


LOG_FILE_NAME = "file_processing.log"


def get_file_stats(file_path):
    """
    Count lines and find maximum line length in a file.

    Args:
        file_path: Path to the file to analyze

    Returns:
        tuple: (line_count, max_line_length)
    """
    line_count = 0
    max_line_length = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_count += 1
            # Don't include newline character in length
            line_length = len(line.rstrip("\n\r"))
            max_line_length = max(max_line_length, line_length)

    return line_count, max_line_length


def generate_processed_filename(original_path):
    """
    Generate a unique filename with timestamp for the processed directory.

    Args:
        original_path: Path object of the original file

    Returns:
        str: New filename with timestamp
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = original_path.stem
    suffix = original_path.suffix
    return f"{stem}_{timestamp}{suffix}"


def log_result(log_file, result):
    """
    Append a processing result to the log file.

    Args:
        log_file: Path to the log file
        result: Dictionary containing processing result
    """
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")


def process_file(file_path, processed_dir, log_file):
    """
    Process a single file: get stats, move to processed, log result.

    Args:
        file_path: Path to the file to process
        processed_dir: Path to the processed directory
        log_file: Path to the log file

    Returns:
        dict: Processing result
    """
    result = {
        "timestamp": datetime.now().isoformat(),
        "original_file": str(file_path),
        "status": "error",
    }

    try:
        # Get file statistics
        line_count, max_line_length = get_file_stats(file_path)

        # Generate new filename with timestamp
        new_filename = generate_processed_filename(file_path)
        new_path = processed_dir / new_filename

        # Move file to processed directory
        shutil.move(str(file_path), str(new_path))

        # Update result
        result.update(
            {
                "status": "success",
                "processed_file": str(new_path),
                "line_count": line_count,
                "max_line_length": max_line_length,
                "file_size": new_path.stat().st_size,
            }
        )

    except UnicodeDecodeError as e:
        result["error"] = f"File encoding error (not UTF-8): {str(e)}"
    except PermissionError as e:
        result["error"] = f"Permission denied: {str(e)}"
    except Exception as e:
        result["error"] = str(e)

    # Log the result
    log_result(log_file, result)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Scan upload directory, process files, move to processed directory",
        add_help=True,
    )
    parser.add_argument(
        "base_dir",
        type=str,
        help="Base directory containing upload/ and processed/ subdirectories",
    )

    args = parser.parse_args()

    try:
        # Setup directories
        base_dir = Path(args.base_dir)
        upload_dir = base_dir / "upload"
        processed_dir = base_dir / "processed"
        log_file = base_dir / LOG_FILE_NAME

        # Validate base directory exists
        if not base_dir.exists():
            print(
                json.dumps(
                    {"error": "Base directory not found", "path": str(base_dir)}
                ),
                file=sys.stderr,
            )
            return 1

        if not base_dir.is_dir():
            print(
                json.dumps(
                    {"error": "Base path is not a directory", "path": str(base_dir)}
                ),
                file=sys.stderr,
            )
            return 1

        # Validate upload directory exists
        if not upload_dir.exists():
            print(
                json.dumps(
                    {"error": "Upload directory not found", "path": str(upload_dir)}
                ),
                file=sys.stderr,
            )
            return 2

        # Create processed directory if it doesn't exist
        processed_dir.mkdir(parents=True, exist_ok=True)

        # Get all files in upload directory (excluding hidden files and README)
        files_to_process = [
            f
            for f in upload_dir.iterdir()
            if f.is_file() and not f.name.startswith(".") and f.name != "README.md"
        ]

        if not files_to_process:
            # No files to process - this is successful (not an error)
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": "no_files",
                "message": "No files found to process",
            }
            print(json.dumps(result))
            return 0

        # Process each file
        results = []
        for file_path in files_to_process:
            result = process_file(file_path, processed_dir, log_file)
            results.append(result)

        # Summary
        successful = sum(1 for r in results if r["status"] == "success")
        failed = len(results) - successful

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(results),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

        print(json.dumps(summary))

        # Return 0 if all successful, non-zero if any failed
        return 0 if failed == 0 else 3

    except Exception as e:
        print(
            json.dumps({"error": "Unexpected error", "message": str(e)}),
            file=sys.stderr,
        )
        return 5


if __name__ == "__main__":
    sys.exit(main())
