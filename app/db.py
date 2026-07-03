"""Database connection helpers using psycopg2 with raw SQL."""

import os
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.extras

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def _connection_kwargs():
    """Build connection parameters from environment variables."""
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "dbname": os.environ.get("DB_NAME", "rsvp"),
        # "require" for RDS/prod; local dev defaults to "prefer" so the
        # non-SSL postgres container still connects.
        "sslmode": os.environ.get("DB_SSLMODE", "prefer"),
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


def apply_schema(retries=30, delay=1.0):
    """Apply the idempotent schema.sql, waiting for the database to come up."""
    sql = SCHEMA_PATH.read_text()
    for attempt in range(retries):
        try:
            with get_cursor(commit=True) as cur:
                cur.execute(sql)
            return
        except psycopg2.OperationalError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)
