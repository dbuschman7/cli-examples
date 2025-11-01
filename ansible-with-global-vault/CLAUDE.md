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

## Ansible Commands

All Ansible commands should be run within the activated virtual environment.

**Run playbooks:**
```bash
ansible-playbook <playbook.yml>
```

**Run with vault:**
```bash
ansible-playbook --ask-vault-pass <playbook.yml>
# Or with vault password file:
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

## Ansible Vault Commands

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

## Project Structure

This repository follows standard Ansible directory structure conventions for roles and playbooks with global vault integration.
