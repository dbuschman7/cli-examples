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

All scripts require parameters and will display usage help if called without arguments.

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

This repository follows standard Ansible directory structure conventions for roles and playbooks with global vault integration.
