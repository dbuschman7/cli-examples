#!/usr/bin/env python3
"""
Setup verification script for FreeRADIUS admin tools.

This script checks:
1. Python dependencies are installed
2. Environment variables are configured
3. Database connection works
4. Required FreeRADIUS tables exist
"""

import sys
import os


def check_dependencies():
    """Check if required Python packages are installed."""
    print("Checking Python dependencies...")
    missing = []

    try:
        import psycopg2

        print("  ✓ psycopg2 installed")
    except ImportError:
        print("  ✗ psycopg2 missing")
        missing.append("psycopg2-binary")

    try:
        import pandas

        print("  ✓ pandas installed")
    except ImportError:
        print("  ✗ pandas missing")
        missing.append("pandas")

    try:
        import tabulate

        print("  ✓ tabulate installed")
    except ImportError:
        print("  ✗ tabulate missing")
        missing.append("tabulate")

    try:
        import dotenv

        print("  ✓ python-dotenv installed")
    except ImportError:
        print("  ✗ python-dotenv missing")
        missing.append("python-dotenv")

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False

    return True


def check_env_file():
    """Check if .env file exists and has required variables."""
    print("\nChecking environment configuration...")

    if not os.path.exists(".env"):
        print("  ⚠ .env file not found")
        print("  Create it with: cp .env.example .env")
        print("  Then edit with your database credentials")
        return False

    print("  ✓ .env file exists")

    # Load environment variables
    from dotenv import load_dotenv

    load_dotenv()

    required_vars = [
        "RADIUS_DB_HOST",
        "RADIUS_DB_PORT",
        "RADIUS_DB_NAME",
        "RADIUS_DB_USER",
        "RADIUS_DB_PASSWORD",
    ]

    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value == "your_secure_password_here":
            print(f"  ✗ {var} not configured")
            missing_vars.append(var)
        else:
            # Mask password
            if "PASSWORD" in var:
                display_value = "****" + value[-4:] if len(value) > 4 else "****"
            else:
                display_value = value
            print(f"  ✓ {var} = {display_value}")

    if missing_vars:
        print(f"\nPlease configure these variables in .env: {', '.join(missing_vars)}")
        return False

    return True


def check_database():
    """Check database connectivity and FreeRADIUS tables."""
    print("\nChecking database connection...")

    try:
        from radius_db import RadiusDB

        db = RadiusDB()

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                # Check PostgreSQL version
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                print(f"  ✓ Connected to PostgreSQL")
                print(f"    {version[:80]}...")

                # Check FreeRADIUS tables
                required_tables = [
                    "nas",
                    "radcheck",
                    "radreply",
                    "radacct",
                    "radusergroup",
                ]

                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = ANY(%s)
                    ORDER BY table_name;
                """,
                    (required_tables,),
                )

                found_tables = [row[0] for row in cur.fetchall()]

                print("\n  FreeRADIUS tables:")
                for table in required_tables:
                    if table in found_tables:
                        print(f"    ✓ {table}")
                    else:
                        print(f"    ✗ {table} (missing)")

                missing_tables = set(required_tables) - set(found_tables)
                if missing_tables:
                    print(f"\n  ⚠ Missing tables: {', '.join(missing_tables)}")
                    print("  Install FreeRADIUS schema if needed")
                    return False

        return True

    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("FreeRADIUS Admin Tools - Setup Verification")
    print("=" * 70)
    print()

    checks = [
        ("Dependencies", check_dependencies),
        ("Environment", check_env_file),
        ("Database", check_database),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Error during {name} check: {e}")
            results.append((name, False))
        print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20} {status}")
        if not result:
            all_passed = False

    print()

    if all_passed:
        print("✓ All checks passed! You're ready to use the FreeRADIUS admin tools.")
        print("\nQuick start:")
        print("  python nas_admin.py list")
        print("  python user_admin.py list")
        print("  python disabled_users.py")
        return 0
    else:
        print("✗ Some checks failed. Please resolve the issues above.")
        print("\nRefer to QUICKSTART.md or README.md for help.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
