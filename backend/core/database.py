"""
Database connection and utilities.
Supports both SQLite (development) and PostgreSQL (production).
"""

from __future__ import annotations

import sqlite3
import logging
from typing import Optional

from .config import DATABASE_URL, DB_PATH

logger = logging.getLogger(__name__)


class DBConn:
    """Thin adapter — presents a sqlite3-like execute() interface over psycopg2 or sqlite3."""

    def __init__(self):
        if DATABASE_URL:
            import psycopg2
            import psycopg2.extras
            self._raw = psycopg2.connect(DATABASE_URL)
            self._cur = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            self._is_pg = True
        else:
            self._raw = sqlite3.connect(DB_PATH)
            self._raw.row_factory = sqlite3.Row
            self._is_pg = False

    def execute(self, sql: str, params=()):
        if self._is_pg:
            sql = sql.replace("?", "%s")
            if "INSERT OR IGNORE" in sql:
                sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
                sql = sql.rstrip("; ") + " ON CONFLICT DO NOTHING"
            sql = (sql
                   .replace("is_active=1", "is_active=TRUE")
                   .replace("is_active=0", "is_active=FALSE")
                   .replace("is_active = 1", "is_active = TRUE")
                   .replace("is_active = 0", "is_active = FALSE"))
            self._cur.execute(sql, params if params else None)
            return self._cur
        return self._raw.execute(sql, params)

    def commit(self):
        self._raw.commit()

    def close(self):
        self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self._raw.rollback()
            else:
                self._raw.commit()
        finally:
            self._raw.close()
        return False


def db_conn() -> DBConn:
    """Create a new database connection."""
    return DBConn()


def get_user_by_id(uid: int) -> Optional[dict]:
    """Fetch user by ID."""
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,username,email,full_name,role,department,is_active FROM users WHERE id=?",
            (uid,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_login(username: str) -> Optional[dict]:
    """Fetch user by username for login."""
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,username,email,full_name,password_hash,role,department,is_active "
            "FROM users WHERE username=?",
            (username,)
        ).fetchone()
    return dict(row) if row else None


def write_audit(user_id: Optional[int], username: str, action: str,
                dept_code: str = None, namespace: str = None, detail: str = None):
    """Write an audit log entry."""
    try:
        with db_conn() as conn:
            conn.execute(
                "INSERT INTO audit_log (user_id,username,action,dept_code,namespace,detail) "
                "VALUES (?,?,?,?,?,?)",
                (user_id, username, action, dept_code, namespace, detail)
            )
            conn.commit()
    except Exception as exc:
        logger.warning("Failed to write audit log: %s", exc)


def init_db():
    """Initialize database tables."""
    from .migrations import run_migrations
    run_migrations()
