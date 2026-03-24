# FreeRADIUS PostgreSQL Administration Tools

Python scripts for administering a FreeRADIUS server configured with a PostgreSQL database backend.

## Features

### 📡 NAS Administration (`nas_admin.py`)
Manage Network Access Servers (NAS devices) in your RADIUS infrastructure:
- **Add** new NAS entries with hostname, shared secret, and configuration
- **Remove** NAS entries from the database
- **Lookup** specific NAS details
- **List** all configured NAS devices
- **Stats** - View NAS usage statistics from accounting data

### 👤 User Administration (`user_admin.py`)
Manage RADIUS user accounts:
- **Add** new users with passwords (cleartext, crypt, or MD5)
- **Remove** users and all associated data
- **Enable/Disable** user accounts
- **Lookup** specific user details
- **List** all users (with filtering options)
- **Stats** - View user activity and usage statistics

### 🚫 Disabled Users Report (`disabled_users.py`)
Track and analyze disabled user accounts:
- View all currently disabled users
- Sort by how long users have been disabled
- Filter by time period (e.g., last 7 days)
- Detailed view of individual disabled users
- Usage statistics and session history
- Export as JSON or CSV

## Prerequisites

- Python 3.8 or higher
- FreeRADIUS server with PostgreSQL backend
- Network access to the PostgreSQL database
- Database credentials with appropriate permissions

## Installation

1. **Navigate to project directory:**
   ```bash
   cd radius-report
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv ../.venv
   source activate.sh
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure database connection:**
   
   Create a `.env` file in the project directory:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your database credentials:
   ```env
   RADIUS_DB_HOST=localhost
   RADIUS_DB_PORT=5432
   RADIUS_DB_NAME=radius
   RADIUS_DB_USER=radius
   RADIUS_DB_PASSWORD=your_secure_password_here
   ```

5. **Test database connection:**
   ```bash
   python radius_db.py
   ```

## Usage

### NAS Administration

```bash
# Add a new NAS
python nas_admin.py add \
    --nasname switch1.example.com \
    --shortname switch1 \
    --secret mysecretkey123 \
    --server 192.168.1.10 \
    --type cisco

# List all NAS devices
python nas_admin.py list

# List with secrets visible (be careful!)
python nas_admin.py list --show-secrets

# Lookup specific NAS
python nas_admin.py lookup --nasname switch1.example.com

# Remove a NAS
python nas_admin.py remove --nasname switch1.example.com

# Show NAS usage statistics
python nas_admin.py stats
```

### User Administration

```bash
# Add a new user
python user_admin.py add --username john --password secret123

# Add a user in disabled state
python user_admin.py add --username jane --password pass456 --disabled

# Disable a user
python user_admin.py disable --username john

# Enable a user
python user_admin.py enable --username john

# Lookup specific user
python user_admin.py lookup --username john

# List all users
python user_admin.py list

# List only enabled users
python user_admin.py list --no-disabled

# List only disabled users
python user_admin.py list --disabled-only

# Remove a user
python user_admin.py remove --username john

# Show user usage statistics
python user_admin.py stats
```

### Disabled Users Report

```bash
# Show all disabled users
python disabled_users.py

# Show users disabled in the last 7 days
python disabled_users.py --days 7

# Show users disabled in the last 30 days
python disabled_users.py --days 30

# Get detailed information about a specific disabled user
python disabled_users.py --username john

# Export to JSON
python disabled_users.py --format json > disabled_users.json

# Export to CSV
python disabled_users.py --format csv > disabled_users.csv
```

## Database Schema

These tools work with the standard FreeRADIUS PostgreSQL schema. Required tables:

- **`nas`** - Network Access Servers configuration
- **`radcheck`** - User authentication data
- **`radreply`** - User reply attributes (optional)
- **`radusergroup`** - User group memberships (optional)
- **`radacct`** - Accounting/session data

## Security Considerations

### Environment Variables
- **Never commit** `.env` file to version control
- Store database credentials securely
- Use read-only database user when possible for reporting scripts
- Use separate credentials for admin vs reporting operations

### Password Storage
Users can be created with different password types:
- **Cleartext-Password** - Stored in plain text (default, not recommended for production)
- **Crypt-Password** - Unix crypt() hashed
- **MD5-Password** - MD5 hashed

For production, consider using PAP with encrypted connections or EAP methods.

### NAS Shared Secrets
- Shared secrets are displayed masked by default in list operations
- Use `--show-secrets` flag only when necessary
- Store secrets with appropriate database permissions

## Architecture

### Module Structure

```
radius-report/
├── radius_db.py          # Database connection module
├── nas_admin.py          # NAS administration
├── user_admin.py         # User administration
├── disabled_users.py     # Disabled users report
├── requirements.txt      # Python dependencies
├── activate.sh          # Virtual environment activation
├── .env.example         # Environment variables template
└── README.md            # This file
```

### Database Connection

All scripts use `radius_db.py` which provides:
- Connection pooling via context managers
- Environment variable configuration
- Query execution helpers
- Error handling

### Common Patterns

All admin scripts follow consistent patterns:
- Subcommand-based CLI (add, remove, list, etc.)
- Table-formatted output using `tabulate`
- Error handling with user-friendly messages
- Support for multiple output formats where applicable

## Troubleshooting

### Connection Issues

**Problem:** `Database connection failed`

**Solutions:**
- Verify database is running: `systemctl status postgresql`
- Check network connectivity: `ping <db_host>`
- Verify credentials in `.env` file
- Check PostgreSQL `pg_hba.conf` allows connections
- Verify firewall rules allow PostgreSQL port (default: 5432)

### Permission Issues

**Problem:** `Permission denied` errors

**Solutions:**
- Ensure database user has appropriate grants:
  ```sql
  GRANT SELECT, INSERT, UPDATE, DELETE ON nas, radcheck, radreply, radusergroup TO radius;
  GRANT SELECT ON radacct TO radius;
  ```

### Missing Tables

**Problem:** `relation "nas" does not exist`

**Solutions:**
- Install FreeRADIUS PostgreSQL schema:
  ```bash
  psql -U radius -d radius -f /etc/raddb/mods-config/sql/main/postgresql/schema.sql
  ```

## Advanced Usage

### Batch Operations

Add multiple users from a file:
```bash
while IFS=, read -r username password; do
    python user_admin.py add --username "$username" --password "$password"
done < users.csv
```

### Monitoring Script

Create a cron job to track disabled users:
```bash
# Add to crontab: daily report of users disabled in last 24 hours
0 9 * * * cd /path/to/radius-report && python disabled_users.py --days 1 | mail -s "Daily Disabled Users Report" admin@example.com
```

### Integration with Other Tools

Export data for analysis:
```bash
# Export disabled users to JSON for processing
python disabled_users.py --format json > /tmp/disabled.json

# Use jq to analyze
cat /tmp/disabled.json | jq '.[] | select(.days_disabled > 30)'
```

## Dependencies

- **psycopg2-binary** - PostgreSQL adapter for Python
- **pandas** - Data analysis and manipulation
- **tabulate** - Pretty-print tabular data
- **python-dotenv** - Environment variable management

## Contributing

To extend functionality:

1. Follow existing patterns in admin scripts
2. Use `RadiusDB` class for all database operations
3. Implement proper error handling
4. Use `tabulate` for formatted output
5. Add command-line help text and examples
6. Update this README with new features

## FreeRADIUS Schema Reference

### Key Tables

**nas table:**
```sql
id, nasname, shortname, type, ports, secret, server, community, description
```

**radcheck table:**
```sql
id, username, attribute, op, value
```

**radacct table:**
```sql
radacctid, acctsessionid, acctuniqueid, username, groupname, realm,
nasipaddress, nasportid, nasporttype, acctstarttime, acctstoptime,
acctsessiontime, acctauthentic, connectinfo_start, connectinfo_stop,
acctinputoctets, acctoutputoctets, calledstationid, callingstationid,
acctterminatecause, servicetype, framedprotocol, framedipaddress
```

## License

This project is intended for system administration of FreeRADIUS servers.

## Support

For issues or questions:
1. Check FreeRADIUS documentation: https://freeradius.org/documentation/
2. Review PostgreSQL logs for database errors
3. Use `--help` flag on any script for detailed usage
4. Test database connection with `python radius_db.py`
