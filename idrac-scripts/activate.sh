#!/bin/bash
# Activate the Python virtual environment for iDRAC scripts
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
    # Check if packages are installed
    if ! python -c "import requests, dotenv" 2>/dev/null; then
        echo ""
        echo "Installing requirements..."
        pip install -q -r "$SCRIPT_DIR/requirements.txt"
        
        if [ $? -eq 0 ]; then
            echo "✓ Requirements installed"
        else
            echo "⚠ Warning: Some requirements may not have installed correctly"
        fi
    fi
fi

echo ""
echo "Available tools:"
echo "  python idrac_client.py     # Test iDRAC connection"
echo "  python hostfile.py          # Manage host files"

# Check for .env file
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo ""
    echo "⚠ Note: .env file not found"
    echo "  Copy .env-example to .env and configure your credentials"
    echo "  cp .env-example .env"
fi
