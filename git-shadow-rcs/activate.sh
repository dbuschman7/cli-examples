#!/bin/bash
# Activate the Python virtual environment for RCS to Git monitor
# Creates local .venv if it doesn't exist and installs requirements

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    
    echo "✓ Virtual environment created"
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "✓ Virtual environment activated"
echo "Python: $(which python)"

# Check if requirements need to be installed
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    # No Python dependencies required, but check for system commands
    echo "Checking system dependencies..."
    
    missing_deps=()
    
    if ! command -v rlog &> /dev/null; then
        missing_deps+=("rlog")
    fi
    
    if ! command -v co &> /dev/null; then
        missing_deps+=("co")
    fi
    
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "⚠ Warning: Missing required system commands: ${missing_deps[*]}"
        echo "  Install RCS on macOS:    brew install rcs"
        echo "  Install RCS on Linux:    sudo apt-get install rcs"
    else
        echo "✓ All system dependencies found"
    fi
fi

echo ""
echo "Available tools:"
echo "  python rcs_monitor.py --help              # Main monitoring script"
echo "  python generate-authors-from-rcs.py --help # Generate authors file"
echo "  python rcs_parser.py <rcs_dir>            # Test RCS parser"
echo "  python git_importer.py <rcs> <git> [authors] # Test importer"
echo "  python author_map.py <authors>            # Test author mappings"
echo "  python hostfile.py          # Manage host files"

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo ""
    echo "⚠ Note: .env file not found"
    echo "  Copy .env-example to .env and configure your credentials"
    echo "  cp .env-example .env"
fi
