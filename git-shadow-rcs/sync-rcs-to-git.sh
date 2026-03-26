#!/bin/bash
#
# sync-rcs-to-git.sh
# 
# Wrapper script for running RCS to Git sync as a cron job
#
# To set up as a cron job, add to crontab:
#   crontab -e
# 
# Then add a line like:
#   0 */2 * * * /path/to/this/script/sync-rcs-to-git.sh
#
# This example runs every 2 hours.
#

# ============================================================
# CONFIGURATION - Update these paths for your environment
# ============================================================

# Directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Path to RCS root directory (where RCS files are located)
RCS_ROOT="/path/to/rcs/directory"

# Path to Git repository (where commits will be imported)
GIT_REPO="/path/to/git/repository"

# Path to author mapping file (optional)
AUTHORS_FILE="$SCRIPT_DIR/authors.txt"

# Git branch to import into
BRANCH="master"

# Log file location
LOG_FILE="/var/log/rcs-sync.log"

# ============================================================
# Script execution - typically no need to modify below
# ============================================================

# Ensure log file exists and is writable
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="/tmp/rcs-sync.log"

# Log timestamp
echo "========================================" >> "$LOG_FILE"
echo "Sync started: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Activate Python virtual environment
cd "$SCRIPT_DIR"
source activate.sh >> "$LOG_FILE" 2>&1

# Build command
CMD="python rcs_monitor.py --rcs-root \"$RCS_ROOT\" --git-repo \"$GIT_REPO\" --branch \"$BRANCH\""

# Add authors file if it exists
if [ -f "$AUTHORS_FILE" ]; then
    CMD="$CMD --authors \"$AUTHORS_FILE\""
fi

# Run the sync
echo "Running: $CMD" >> "$LOG_FILE"
eval $CMD >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

# Log completion
echo "Sync completed: $(date) (exit code: $EXIT_CODE)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Optional: rotate log file if it gets too large (keep last 1000 lines)
if [ $(wc -l < "$LOG_FILE") -gt 1000 ]; then
    tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp"
    mv "$LOG_FILE.tmp" "$LOG_FILE"
fi

exit $EXIT_CODE
