#!/bin/bash
# Activate the Python virtual environment for FreeRADIUS admin tools

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/../.venv"

if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    echo "✓ Virtual environment activated"
    echo "Python: $(which python)"
    echo ""
    echo "Available tools:"
    echo "  python nas_admin.py --help      # NAS administration"
    echo "  python user_admin.py --help     # User administration"
    echo "  python disabled_users.py --help # Disabled users report"
    echo "  python radius_db.py             # Test database connection"
else
    echo "❌ Virtual environment not found at $VENV_DIR"
    echo "Create it with: python3 -m venv $VENV_DIR"
    echo "Then install dependencies: pip install -r requirements.txt"
    exit 1
fi
