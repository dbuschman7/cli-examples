#!/bin/bash
# Activate the Python virtual environment for the DNS zone parser

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/../.venv"

if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    echo "✓ Virtual environment activated"
    echo "Python: $(which python)"
    echo "You can now run: python zone_parser.py --help"
else
    echo "❌ Virtual environment not found at $VENV_DIR"
    echo "Create it with: python3 -m venv $VENV_DIR"
    echo "Then install dependencies: pip install -r requirements.txt"
    exit 1
fi
