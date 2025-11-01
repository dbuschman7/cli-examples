# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Ansible example project demonstrating roles and global vault usage. The repository uses a Python virtual environment for isolated Ansible installation.

## Environment Setup

The project uses a Python virtual environment located in `.venv/` with Ansible installed.

**Activate the environment:**
```bash
source activate.sh
```

Or manually:
```bash
source .venv/bin/activate
```

**Install/update Ansible:**
```bash
.venv/bin/pip install ansible
```

**Verify Ansible installation:**
```bash
.venv/bin/ansible --version
```

## Configuration

The project uses `ansible.cfg` in the root directory with the following key settings:
- **Vault password file**: `.vault/password` - automatically used for all vault operations
- **Inventory location**: `inventory` directory
- **Roles path**: `roles` directory
- **Output format**: YAML for better readability

**Important**: The vault password file (`.vault/password`) contains the encryption key. Keep this file secure and do not commit it to version control.

## Ansible Commands

All Ansible commands should be run within the activated virtual environment.

**Run playbooks:**
```bash
ansible-playbook <playbook.yml>
# Vault password is automatically loaded from .vault/password
```

**Override vault password:**
```bash
ansible-playbook --ask-vault-pass <playbook.yml>
# Or use a different vault password file:
ansible-playbook --vault-password-file <path> <playbook.yml>
```

**Test inventory:**
```bash
ansible-inventory --list -i <inventory>
```

**Check playbook syntax:**
```bash
ansible-playbook --syntax-check <playbook.yml>
```

**Dry run:**
```bash
ansible-playbook --check <playbook.yml>
```

## Vault Helper Scripts

The `bin/` directory contains convenience scripts for common vault operations. These scripts automatically use the project's venv and handle parameter validation.

**View encrypted file:**
```bash
./bin/vault-view <file>
# Example: ./bin/vault-view group_vars/all/vault.yml
```

**Edit encrypted file:**
```bash
./bin/vault-edit <file>
# Example: ./bin/vault-edit group_vars/all/vault.yml
```

**Get variable value from vault:**
```bash
./bin/vault-get-var <variable-name-pattern> [vault-file]
# Returns only the value on stdout (no variable name)
# Supports grep patterns for variable names
# Example: ./bin/vault-get-var vault_db_password
# Example: ./bin/vault-get-var vault_database_production_host
# Errors on stderr with exit code 1 if multiple or no matches found
```

**Add variable to vault:**
```bash
./bin/vault-add-var [vault-file]
# Defaults to group_vars/all/vault.yml if no file specified
# Prompts for: feature, group, name, value
# Creates variable: vault_{feature}_{group}_{name}
# Example: feature=database, group=production, name=host
#          Result: vault_database_production_host: "value"
```

**Change vault password:**
```bash
./bin/vault-password-change <new-password>
# Example: ./bin/vault-password-change my-new-secure-password
# Creates timestamped backup of old password (.vault/password.YYYYMMDD_HHMMSS)
```

**Rekey encrypted file (change password):**
```bash
./bin/vault-rekey <file>
# Example: ./bin/vault-rekey group_vars/all/vault.yml
# Note: Run vault-password-change first, then rekey all encrypted files
```

Most scripts require parameters and will display usage help if called without required arguments. The vault-add-var script uses interactive prompts.

## Ansible Vault Commands

All vault commands automatically use the password from `.vault/password` as configured in `ansible.cfg`.

**Create encrypted file:**
```bash
ansible-vault create <file>
```

**Edit encrypted file:**
```bash
ansible-vault edit <file>
```

**Encrypt existing file:**
```bash
ansible-vault encrypt <file>
```

**Decrypt file:**
```bash
ansible-vault decrypt <file>
```

**View encrypted file:**
```bash
ansible-vault view <file>
```

**Change vault password:**
```bash
# Update the password in .vault/password, then rekey existing files:
ansible-vault rekey <file>
```

## Project Structure

```
.
├── .vault/                      # Vault password storage
│   └── password                 # Vault password file (default: "changeme")
├── .venv/                       # Python virtual environment
├── activate.sh                  # Convenience script to activate venv
├── ansible.cfg                  # Ansible configuration with vault settings
├── bin/                         # Vault helper scripts
│   ├── vault-view               # View encrypted vault files
│   ├── vault-edit               # Edit encrypted vault files
│   ├── vault-get-var            # Get single variable value from vault
│   ├── vault-add-var            # Add variable to vault (interactive)
│   ├── vault-password-change    # Change vault password with backup
│   └── vault-rekey              # Rekey files after password change
├── group_vars/                  # Group variables
│   └── all/                     # Variables for all hosts
│       └── vault.yml            # Encrypted secrets (vault_* variables)
├── inventory/                   # Inventory files (to be created)
├── roles/                       # Ansible roles (to be created)
└── CLAUDE.md                    # This file

Note: This is an example repository. The .vault/password file is committed for
demonstration purposes. In production, always add .vault/password to .gitignore.
```

## Variable Naming Convention

All vault variables follow the pattern: `vault_{feature}_{group}_{name}`

Examples:
- `vault_database_production_host` - Production database host
- `vault_api_staging_key` - Staging API key
- `vault_app_secret_key` - Application secret key

This naming convention:
- Makes vault variables easily identifiable
- Provides clear organization by feature and environment
- Prevents naming conflicts with non-sensitive variables

## Current Vault Contents

The example vault file (`group_vars/all/vault.yml`) contains:
- Database credentials (user, password, host, port)
- API keys and secrets
- AWS credentials (example keys)
- Application secrets (Flask, JWT)
- SSH deploy keys
- Custom added variables (database_production_host, api_staging_key)

## Development Workflow

1. **Setup**: Run `source activate.sh` to activate the Python environment
2. **View secrets**: Use `./bin/vault-view group_vars/all/vault.yml`
3. **Add secrets**: Use `./bin/vault-add-var` for interactive addition
4. **Get secrets**: Use `./bin/vault-get-var <variable-name>` in scripts
5. **Edit secrets**: Use `./bin/vault-edit group_vars/all/vault.yml`
6. **Change password**: Use `./bin/vault-password-change`, then rekey all files

## Session Information

**Ansible Version**: 12.1.0 (core 2.19.3)
**Python Version**: 3.13.5
**Vault Password**: changeme (default, change for production use)
**Config File**: ./ansible.cfg (automatically detected by Ansible)
