#!/bin/bash
# Activation script for tree_of_animals Python virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Install/update dependencies
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -r "$SCRIPT_DIR/requirements.txt"
fi

echo "Python virtual environment activated!"
echo "Python location: $(which python)"
echo "Python version: $(python --version)"
echo ""
echo "To deactivate, run: deactivate"
