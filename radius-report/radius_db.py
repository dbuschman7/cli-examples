#!/usr/bin/env python3
"""
FreeRADIUS Database Connection Module

Provides database connection and common query functions for FreeRADIUS
PostgreSQL database administration.
"""

import psycopg2
import psycopg2.extras
import os
from typing import Optional, Dict, List, Any
from contextlib import contextmanager
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class RadiusDB:
    """Database connection manager for FreeRADIUS PostgreSQL database."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize database connection parameters.

        Parameters are loaded from environment variables if not provided:
        - RADIUS_DB_HOST (default: localhost)
        - RADIUS_DB_PORT (default: 5432)
        - RADIUS_DB_NAME (default: radius)
        - RADIUS_DB_USER (default: radius)
        - RADIUS_DB_PASSWORD (required)
        """
        self.host = host or os.getenv("RADIUS_DB_HOST", "localhost")
        self.port = port or int(os.getenv("RADIUS_DB_PORT", "5432"))
        self.database = database or os.getenv("RADIUS_DB_NAME", "radius")
        self.user = user or os.getenv("RADIUS_DB_USER", "radius")
        self.password = password or os.getenv("RADIUS_DB_PASSWORD", "")

        if not self.password:
            raise ValueError(
                "Database password is required. "
                "Set RADIUS_DB_PASSWORD environment variable or pass password parameter."
            )

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Usage:
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT ...")
        """
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as list of dictionaries.

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            List of dictionaries with column names as keys
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount


def test_connection():
    """Test database connectivity."""
    try:
        db = RadiusDB()
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                print(f"✓ Successfully connected to PostgreSQL")
                print(f"  Version: {version}")

                # Test if FreeRADIUS tables exist
                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name IN ('nas', 'radcheck', 'radreply', 'radacct', 'radgroupcheck')
                    ORDER BY table_name;
                """
                )
                tables = [row[0] for row in cur.fetchall()]

                if tables:
                    print(f"\n✓ Found FreeRADIUS tables: {', '.join(tables)}")
                else:
                    print("\n⚠ Warning: No FreeRADIUS tables found in database")

        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing FreeRADIUS Database Connection")
    print("=" * 60)
    test_connection()
