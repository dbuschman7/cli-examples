#!/bin/bash
# Activation script for Ansible virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "${SCRIPT_DIR}/.venv/bin/activate"

echo "Virtual environment activated!"
echo "Python: $(which python)"
echo "Ansible version:"
ansible --version 2>/dev/null || echo "Ansible not yet installed or not in PATH"
