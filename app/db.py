"""Database connection helpers using psycopg2 with raw SQL."""

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras


def _connection_kwargs():
    """Build connection parameters from environment variables."""
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "dbname": os.environ.get("DB_NAME", "rsvp"),
    }


@contextmanager
def get_cursor(commit=False):
    """Yield a dict-style cursor, handling connection/commit/cleanup.

    Usage:
        with get_cursor() as cur:
            cur.execute("SELECT ...")
            rows = cur.fetchall()
    """
    conn = psycopg2.connect(**_connection_kwargs())
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ping():
    """Run a trivial query to confirm the database is reachable."""
    with get_cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
