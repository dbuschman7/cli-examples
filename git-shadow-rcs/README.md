# Git Shadow RCS

A Python-based tool that monitors RCS (Revision Control System) directories and automatically syncs commits to a Git repository. This tool is designed to run as a cron job to maintain a Git mirror of an actively-used RCS directory tree.

## Overview

This project provides a "shadow" Git repository that tracks changes from an RCS-managed codebase. It's particularly useful for:

- Migrating from RCS to Git incrementally
- Maintaining a Git mirror of legacy RCS repositories
- Enabling modern Git workflows alongside existing RCS systems
- Providing Git-based backup and history visualization for RCS projects

## Features

- **Incremental Sync**: Only imports new RCS commits since last sync
- **Initial Import**: Can import complete RCS history from any point in time
- **Commit Coalescing**: Merges multi-file commits that occur within a time window (default 5 minutes)
- **Author Mapping**: Maps RCS usernames to Git author format (Name <email>)
- **State Tracking**: Maintains sync state to avoid duplicate imports
- **Dry Run Mode**: Preview what would be imported without making changes
- **Cron-Friendly**: Designed to run unattended as a scheduled job

## Requirements

### System Commands

The following commands must be installed and available in your PATH:

- `rlog` - RCS log viewer (from RCS package)
- `co` - RCS checkout command (from RCS package)
- `git` - Git version control system

#### Installing RCS

**macOS:**
```bash
brew install rcs
```

**Ubuntu/Debian:**
```bash
sudo apt-get install rcs
```

**RHEL/CentOS:**
```bash
sudo yum install rcs
```

### Python

Python 3.7 or higher is required. No external Python packages are needed - the project uses only the standard library.

## Setup

1. **Clone or copy this project**

2. **Activate the Python environment:**
   ```bash
   source activate.sh
   ```

3. **Initialize a Git repository** (if not already done):
   ```bash
   cd /path/to/your/git/repo
   git init
   ```

4. **Generate an author mapping file** (recommended):

   Automatically extract authors from RCS logs:
   ```bash
   python generate-authors-from-rcs.py --rcs-root /path/to/rcs --output authors.txt --stats
   ```
   
   Then edit `authors.txt` to add real names and email addresses.
   
   Or create manually with this format:
   ```
   # Map RCS usernames to Git author format
   jdoe = John Doe <jdoe@example.com>
   admin = System Admin <admin@example.com>
   root = Root User <root@example.com>
   ```

## Generating Author Mappings

The `generate-authors-from-rcs.py` script automatically creates an initial `authors.txt` file by scanning RCS commit logs:

### Basic Usage

```bash
# Generate authors file with statistics
python generate-authors-from-rcs.py \
  --rcs-root /path/to/rcs \
  --output authors.txt \
  --stats
```

### Options

- `--dry-run` - Preview authors without creating file
- `--stats` - Show commit count per author
- `--domain DOMAIN` - Use custom email domain (default: localhost)
- `--append` - Add new authors to existing file
- `--verbose` - Show detailed progress

### Example Output

```
Found 3 unique authors

Commit statistics per author:
--------------------------------------------------
  admin                     45 commits
  jdoe                      23 commits
  root                      12 commits
--------------------------------------------------
  Total: 80 commits by 3 authors

Generated 3 author mappings:
======================================================================
  admin                -> Admin <admin@localhost>               (45 commits)
  jdoe                 -> Jdoe <jdoe@localhost>                (23 commits)
  root                 -> Root <root@localhost>                (12 commits)
======================================================================

✓ Author mappings written to: authors.txt

Next steps:
  1. Edit authors.txt to add real names and email addresses
  2. Use with: rcs_monitor.py --authors authors.txt
```

**After generation**, edit the file to add proper names and emails:

```bash
# Before (auto-generated):
admin = Admin <admin@localhost>

# After (edited with real information):
admin = John Smith <john.smith@company.com>
```

## Usage

### Initial Import

To import the complete RCS history into Git for the first time:

```bash
python rcs_monitor.py \
  --rcs-root /path/to/rcs/directory \
  --git-repo /path/to/git/repo \
  --initial \
  --authors authors.txt
```

**Note:** By default, if no previous sync exists, the tool will only import commits from the last 7 days. Use `--initial` to force import of all history.

### Incremental Sync (for Cron)

To sync only new commits since the last run:

```bash
python rcs_monitor.py \
  --rcs-root /path/to/rcs/directory \
  --git-repo /path/to/git/repo \
  --authors authors.txt
```

### Dry Run

To see what would be imported without making changes:

```bash
python rcs_monitor.py \
  --rcs-root /path/to/rcs/directory \
  --git-repo /path/to/git/repo \
  --dry-run
```

### Command Line Options

```
--rcs-root PATH       Path to RCS root directory (required)
--git-repo PATH       Path to Git repository (required)
--branch BRANCH       Git branch to import into (default: master)
--authors FILE        Path to author mapping file
--commit-fuzz SEC     Time window for coalescing commits in seconds (default: 300)
--initial             Perform initial import of all history
--dry-run             Show what would be done without making changes
--state-file PATH     Path to state file (default: GIT_REPO/.rcs_sync_state.json)
```

## Setting Up as a Cron Job

To run the sync every 2 hours:

1. Create a wrapper script `sync-rcs.sh`:

   ```bash
   #!/bin/bash
   cd /path/to/git-shadow-rcs
   source activate.sh
   
   python rcs_monitor.py \
     --rcs-root /path/to/rcs/directory \
     --git-repo /path/to/git/repo \
     --authors authors.txt \
     >> /var/log/rcs-sync.log 2>&1
   ```

2. Make it executable:
   ```bash
   chmod +x sync-rcs.sh
   ```

3. Add to crontab:
   ```bash
   crontab -e
   ```

   Add this line:
   ```
   0 */2 * * * /path/to/sync-rcs.sh
   ```

## How It Works

### RCS Structure

RCS stores revisions in `,v` files which can be located:
- In the same directory as working files (e.g., `file.txt,v`)
- In an `RCS/` subdirectory (e.g., `RCS/file.txt,v`)

The tool scans for both patterns recursively.

### Import Process

1. **Scan RCS Files**: Find all `,v` files in the directory tree
2. **Parse History**: Use `rlog` to extract revision metadata (date, author, log message)
3. **Filter Revisions**: Only select revisions newer than last sync
4. **Coalesce Commits**: Group revisions with same author/message within time window
5. **Generate Fast-Import**: Create Git fast-import commands
6. **Import to Git**: Pipe commands to `git fast-import`
7. **Update State**: Record sync timestamp for next run

### State File

The sync state is stored in `.rcs_sync_state.json` in the Git repository:

```json
{
  "last_sync": "2026-03-25T10:30:00",
  "revisions_synced": 15,
  "files_synced": 8
}
```

This file tracks when the last sync occurred to avoid re-importing revisions.

## Testing Components

### Generate Author Mappings

```bash
python generate-authors-from-rcs.py --rcs-root /path/to/rcs --stats --dry-run
```

This will scan RCS files and show all unique authors with commit counts, without creating a file.

### Test Author Mapping

```bash
python author_map.py authors.txt
```

This will load and display all author mappings, then test mapping for sample usernames.

### Test RCS Parser

```bash
python rcs_parser.py /path/to/rcs/directory
```

This will show the first few RCS files and their revision history.

### Test Git Importer

```bash
python git_importer.py /path/to/rcs/directory /path/to/git/repo [authors.txt]
```

This generates fast-import commands to stdout without importing. Optionally provide an authors file.

## Project Structure

```
git-shadow-rcs/
├── activate.sh                    # Environment setup script
├── requirements.txt               # Python dependencies (none required)
├── rcs_parser.py                 # RCS file parsing module
├── author_map.py                 # Author mapping module
├── git_importer.py               # Git fast-import generation
├── rcs_monitor.py                # Main monitoring script
├── generate-authors-from-rcs.py  # Generate authors file from RCS logs
├── sync-rcs-to-git.sh            # Cron wrapper script
├── authors.txt                   # Author mapping file (user-created)
├── authors.txt.example           # Example author mapping file
├── README.md                    # This file
└── QUICKSTART.md                # Quick start guide
```

## Troubleshooting

### "rlog: command not found"

Install the RCS package for your operating system (see Requirements section).

### Commits not being coalesced

Increase the `--commit-fuzz` value. The default is 300 seconds (5 minutes). If commits on multiple files occur more than 5 minutes apart, they won't be coalesced.

### Wrong author format

Create or update the `authors.txt` file with proper Git author format:
```
username = Full Name <email@example.com>
```

### State file issues

If the state file becomes corrupted, you can:
- Delete it to start fresh: `rm /path/to/git/repo/.rcs_sync_state.json`
- Or specify a different location with `--state-file`

### Import entire history again

Use the `--initial` flag to ignore the state file and import all RCS history:
```bash
python rcs_monitor.py --rcs-root /path/to/rcs --git-repo /path/to/git --initial
```

## Limitations

- **Branch Support**: Currently only supports single-branch import (typically to master/main)
- **RCS Branches**: RCS branches are not fully supported - only main trunk is imported
- **File Deletion**: Files marked as "dead" in RCS are deleted from Git
- **Binary Files**: Binary file handling depends on RCS configuration

## Reference

This implementation is based on the concepts from [rcs-fast-export](https://github.com/Oblomov/rcs-fast-export), which is written in Ruby. This Python version provides:

- Incremental sync capability for ongoing RCS use
- State tracking to avoid re-importing revisions
- Cron-friendly operation
- Pure Python implementation with no external dependencies

## License

This tool is provided as-is for managing RCS to Git synchronization.

## Contributing

Feel free to extend this tool for your specific needs. Common enhancements might include:

- Support for RCS branches
- Email notifications on sync failures
- Metrics/statistics reporting
- Integration with CI/CD systems
- Support for symbolic tags

---

For questions or issues, please refer to the source code comments or create an issue in your project repository.
