# FreeRADIUS Admin Tools - Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd radius-report
source activate.sh  # If venv exists
# OR
python3 -m venv ../.venv && source activate.sh
pip install -r requirements.txt
```

### 2. Configure Database

```bash
# Copy example config
cp .env.example .env

# Edit with your credentials
nano .env
```

Minimum required configuration:
```env
RADIUS_DB_HOST=your-db-host
RADIUS_DB_PASSWORD=your-password
```

### 3. Test Connection

```bash
python radius_db.py
```

Expected output:
```
✓ Successfully connected to PostgreSQL
  Version: PostgreSQL 14.x ...
✓ Found FreeRADIUS tables: nas, radacct, radcheck, ...
```

## Common Tasks

### Managing NAS Devices

```bash
# Add a switch
python nas_admin.py add \
    --nasname switch1.example.com \
    --shortname switch1 \
    --secret MySecret123

# View all NAS devices
python nas_admin.py list

# Check NAS usage
python nas_admin.py stats
```

### Managing Users

```bash
# Create a user
python user_admin.py add --username alice --password secret123

# Disable a user
python user_admin.py disable --username alice

# Re-enable a user
python user_admin.py enable --username alice

# View all users
python user_admin.py list

# Check user activity
python user_admin.py stats
```

### Monitoring Disabled Users

```bash
# View all disabled users
python disabled_users.py

# Users disabled in last 7 days
python disabled_users.py --days 7

# Detailed info about a user
python disabled_users.py --username alice

# Export to CSV for reporting
python disabled_users.py --format csv > report.csv
```

## Quick Reference

| Task | Command |
|------|---------|
| Add NAS | `python nas_admin.py add --nasname NAME --shortname SHORT --secret SECRET` |
| List NAS | `python nas_admin.py list` |
| NAS stats | `python nas_admin.py stats` |
| Add user | `python user_admin.py add --username USER --password PASS` |
| Disable user | `python user_admin.py disable --username USER` |
| Enable user | `python user_admin.py enable --username USER` |
| List users | `python user_admin.py list` |
| User stats | `python user_admin.py stats` |
| Disabled report | `python disabled_users.py` |
| Recent disabled | `python disabled_users.py --days 7` |

## Troubleshooting

### Can't connect to database
```bash
# Check PostgreSQL is running
systemctl status postgresql

# Test network connection
telnet your-db-host 5432

# Verify credentials
psql -h your-db-host -U radius -d radius
```

### Tables not found
```bash
# Install FreeRADIUS schema
psql -U postgres -d radius -f /etc/raddb/mods-config/sql/main/postgresql/schema.sql
```

### Permission denied
```sql
-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO radius;
```

## Next Steps

1. **Read the full README.md** for detailed documentation
2. **Set up monitoring** - Create cron jobs for daily reports
3. **Batch operations** - Script user creation from CSV files
4. **Integration** - Export data to other systems
5. **Security** - Review and harden database permissions

## Getting Help

```bash
# Any script supports --help
python nas_admin.py --help
python user_admin.py --help
python disabled_users.py --help
```

## Safety Tips

- ⚠️ **Always test on non-production first**
- ⚠️ **Back up database before bulk operations**
- ⚠️ **Never commit .env file to version control**
- ⚠️ **Use read-only credentials for reporting**
- ⚠️ **Audit changes regularly**
