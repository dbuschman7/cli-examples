# Quick Start Guide

Get up and running with Git Shadow RCS in 5 minutes.

## Prerequisites

Install RCS (if not already installed):

**macOS:**
```bash
brew install rcs
```

**Linux:**
```bash
sudo apt-get install rcs  # Ubuntu/Debian
sudo yum install rcs      # RHEL/CentOS
```

## Setup

1. **Activate the environment:**
   ```bash
   cd git-shadow-rcs
   source activate.sh
   ```

2. **Initialize a Git repository** (if needed):
   ```bash
   # Create a new directory for the Git mirror
   mkdir -p /path/to/git/mirror
   cd /path/to/git/mirror
   git init
   ```

2. **Generate author mappings** (recommended):
   ```bash
   cd git-shadow-rcs
   
   # Auto-generate from RCS logs (shows stats)
   python3 generate-authors-from-rcs.py \
     --rcs-root /path/to/rcs/directory \
     --output authors.txt \
     --stats
   
   # Edit the generated file to add real names and emails
   nano authors.txt
   ```

## Quick Test

Test the parser on your RCS directory:

```bash
python3 rcs_parser.py /path/to/rcs/directory
```

This will show you the RCS files found and their revision history.

## Initial Import

Import all RCS history into Git:

```bash
python3 rcs_monitor.py \
  --rcs-root /path/to/rcs/directory \
  --git-repo /path/to/git/mirror \
  --authors authors.txt \
  --initial
```

**Example with actual paths:**
```bash
python3 rcs_monitor.py \
  --rcs-root /usr/local/etc/config \
  --git-repo /home/user/git-mirror \
  --authors authors.txt \
  --initial
```

## Verify Import

Check the Git repository:

```bash
cd /path/to/git/mirror
git log --oneline
git log --stat
```

## Set Up Automatic Sync

1. **Edit the sync script:**
   ```bash
   nano sync-rcs-to-git.sh
   ```
   
   Update these variables:
   ```bash
   RCS_ROOT="/path/to/rcs/directory"
   GIT_REPO="/path/to/git/mirror"
   ```

2. **Test the sync script:**
   ```bash
   ./sync-rcs-to-git.sh
   ```

3. **Add to crontab** (run every 2 hours):
   ```bash
   crontab -e
   ```
   
   Add this line:
   ```
   0 */2 * * * /path/to/git-shadow-rcs/sync-rcs-to-git.sh
   ```

## Daily Usage

Once set up, the cron job will automatically:
1. Check for new RCS commits
2. Import them to Git
3. Log results to `/var/log/rcs-sync.log` (or `/tmp/rcs-sync.log`)

Manual sync anytime:
```bash
python3 rcs_monitor.py \
  --rcs-root /path/to/rcs/directory \
  --git-repo /path/to/git/mirror \
  --authors authors.txt
```

## Troubleshooting

**Can't find rlog command:**
- Install RCS package for your OS (see Prerequisites)

**No commits imported:**
- Check that RCS files exist: `find /path/to/rcs -name "*,v"`
- Use `--dry-run` flag to see what would be imported
- Try `--initial` flag to force import

**Wrong commit authors:**
- Update `authors.txt` with proper mappings
- Format: `username = Full Name <email@example.com>`

**Need to re-import everything:**
```bash
# Delete state file
rm /path/to/git/mirror/.rcs_sync_state.json

# Re-run with --initial
python3 rcs_monitor.py --rcs-root ... --git-repo ... --initial
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Customize commit coalescing with `--commit-fuzz` option
- Set up email notifications for sync failures
- Configure Git remote to push to a central repository

## Common Scenarios

### Scenario 1: First Time Setup
```bash
# 1. Set up environment
source activate.sh

# 2. Create Git repo
mkdir ~/rcs-git-mirror && cd ~/rcs-git-mirror && git init

# 3. Generate author mappings from RCS
cd ~/git-shadow-rcs
python3 generate-authors-from-rcs.py \
  --rcs-root /usr/local/etc \
  --output authors.txt \
  --stats

# 4. Edit authors.txt with real names/emails
nano authors.txt

# 5. Import RCS history
python3 rcs_monitor.py \
  --rcs-root /usr/local/etc \
  --git-repo ~/rcs-git-mirror \
  --authors authors.txt \
  --initial

# 6. Verify
cd ~/rcs-git-mirror && git log
```

### Scenario 2: Daily Monitoring
```bash
# Already set up, just sync new commits
python3 rcs_monitor.py --rcs-root /usr/local/etc --git-repo ~/rcs-git-mirror
```

### Scenario 3: Preview Before Import
```bash
# See what would be imported
python3 rcs_monitor.py --rcs-root /usr/local/etc --git-repo ~/rcs-git-mirror --dry-run
```

### Scenario 4: Check Who Has Been Committing
```bash
# Show RCS commit statistics by author
python3 generate-authors-from-rcs.py \
  --rcs-root /usr/local/etc \
  --stats \
  --dry-run
```

---

That's it! You now have a Git mirror of your RCS repository that stays in sync automatically.
