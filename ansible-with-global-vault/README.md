# Ansible with Global Vault Example

This is an example Ansible project demonstrating best practices for managing secrets using Ansible Vault with a global vault password file and custom helper scripts.

## Features

- **Python Virtual Environment**: Isolated Ansible installation in `.venv/`
- **Global Vault Configuration**: Automatic vault password loading via `ansible.cfg`
- **Helper Scripts**: Six custom bash scripts for vault operations
- **Structured Variable Naming**: Convention-based naming for vault variables
- **Example Vault File**: Pre-configured with sample encrypted secrets

## Quick Start

### 1. Activate the Environment

```bash
source activate.sh
```

This activates the Python virtual environment with Ansible 12.1.0 installed.

### 2. View Encrypted Secrets

```bash
./bin/vault-view group_vars/all/vault.yml
```

Default vault password: `changeme`

### 3. Get a Specific Secret Value

```bash
./bin/vault-get-var vault_db_password
# Output: super_secret_db_password_123
```

### 4. Add a New Secret

```bash
./bin/vault-add-var
```

Follow the interactive prompts to add variables with the naming pattern: `vault_{feature}_{group}_{name}`

## Helper Scripts

All scripts are located in the `bin/` directory:

| Script | Purpose | Usage |
|--------|---------|-------|
| `vault-view` | View encrypted vault file | `./bin/vault-view <file>` |
| `vault-edit` | Edit encrypted vault file | `./bin/vault-edit <file>` |
| `vault-get-var` | Get single variable value | `./bin/vault-get-var <pattern>` |
| `vault-add-var` | Add variable (interactive) | `./bin/vault-add-var [file]` |
| `vault-password-change` | Change vault password | `./bin/vault-password-change <password>` |
| `vault-rekey` | Rekey after password change | `./bin/vault-rekey <file>` |

## Variable Naming Convention

All vault variables follow this pattern:

```
vault_{feature}_{group}_{name}
```

**Examples:**
- `vault_database_production_host`
- `vault_api_staging_key`
- `vault_app_secret_key`

This convention provides:
- Clear identification of sensitive variables
- Organization by feature and environment
- Prevention of naming conflicts

## Project Structure

```
.
├── .vault/
│   └── password              # Vault password file (changeme)
├── .venv/                    # Python virtual environment
├── activate.sh               # Environment activation script
├── ansible.cfg               # Ansible configuration
├── bin/                      # Vault helper scripts (6 scripts)
├── group_vars/
│   └── all/
│       └── vault.yml         # Encrypted secrets
└── README.md                 # This file
```

## Configuration

The project uses `ansible.cfg` for automatic vault password loading:

```ini
[defaults]
vault_password_file = .vault/password
inventory = inventory
roles_path = roles
stdout_callback = yaml
host_key_checking = False
retry_files_enabled = False
```

## Example Vault Contents

The `group_vars/all/vault.yml` file contains example secrets:

- Database credentials (user, password, host, port)
- API keys and secrets
- AWS credentials
- Application secrets (Flask secret key, JWT secret)
- SSH deploy keys

## Usage in Playbooks

Use vault variables in your playbooks like any other variable:

```yaml
- name: Configure database connection
  template:
    src: database.conf.j2
    dest: /etc/app/database.conf
  vars:
    db_host: "{{ vault_db_host }}"
    db_user: "{{ vault_db_user }}"
    db_password: "{{ vault_db_password }}"
```

## Scripting with Vault Variables

The `vault-get-var` script makes it easy to use vault variables in bash scripts:

```bash
#!/bin/bash
# Example script using vault secrets

DB_HOST=$(./bin/vault-get-var vault_database_production_host)
API_KEY=$(./bin/vault-get-var vault_api_key)

echo "Connecting to: $DB_HOST"
curl -H "Authorization: Bearer $API_KEY" https://api.example.com
```

## Changing the Vault Password

1. Change the password file:
   ```bash
   ./bin/vault-password-change new-password
   ```

2. Rekey all encrypted files:
   ```bash
   ./bin/vault-rekey group_vars/all/vault.yml
   ```

The old password is automatically backed up with a timestamp.

## Security Notes

**Important**: This is an example repository. The `.vault/password` file is committed for demonstration purposes.

**In production environments:**
- Add `.vault/password` to `.gitignore`
- Use strong, unique passwords
- Store vault passwords securely (e.g., password manager, CI/CD secrets)
- Rotate vault passwords regularly
- Limit access to vault password files

## Environment Details

- **Ansible Version**: 12.1.0 (core 2.19.3)
- **Python Version**: 3.13.5
- **Jinja Version**: 3.1.6
- **PyYAML Version**: 6.0.3

## License

This is an example project for educational purposes.

## Contributing

This is a demonstration repository. Feel free to use it as a template for your own projects.
