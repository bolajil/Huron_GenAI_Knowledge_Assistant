"""
SQLite → PostgreSQL Migration Script
Run ONCE when you are ready to scale beyond ~200 concurrent users.

Prerequisites:
  pip install psycopg2-binary

Usage:
  export DATABASE_URL="postgresql://huron_user:HuronDB2026!@localhost:5436/huron"
  python migrate_sqlite_to_postgres.py
"""

import os
import sqlite3
import sys
from pathlib import Path

SQLITE_PATH = Path(__file__).parent / "data" / "huron.db"
PG_URL = os.environ.get("DATABASE_URL", "")

TABLES = [
    "users", "departments", "access_requests",
    "audit_log", "query_log", "token_blacklist",
]

# SQLite stores booleans as INTEGER 0/1 — cast these to Python bool before
# inserting into PostgreSQL's BOOLEAN columns.
BOOL_COLS: dict[str, set[str]] = {
    "users":       {"is_active"},
    "departments": {"is_active"},
}

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    full_name     TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    department    TEXT NOT NULL DEFAULT 'general',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_by    INTEGER REFERENCES users(id),
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS departments (
    id            SERIAL PRIMARY KEY,
    code          TEXT UNIQUE NOT NULL,
    display_name  TEXT NOT NULL,
    namespace     TEXT UNIQUE NOT NULL,
    classification TEXT NOT NULL DEFAULT 'internal',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    admin_user_id INTEGER REFERENCES users(id),
    doc_count     INTEGER NOT NULL DEFAULT 0,
    query_count   INTEGER NOT NULL DEFAULT 0,
    user_count    INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS access_requests (
    id             SERIAL PRIMARY KEY,
    requester_id   INTEGER NOT NULL REFERENCES users(id),
    dept_code      TEXT NOT NULL,
    requested_tab  TEXT NOT NULL,
    requested_role TEXT NOT NULL DEFAULT 'user',
    justification  TEXT NOT NULL DEFAULT '',
    status         TEXT NOT NULL DEFAULT 'pending',
    reviewed_by    INTEGER REFERENCES users(id),
    reviewed_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id),
    username   TEXT,
    action     TEXT NOT NULL,
    dept_code  TEXT,
    namespace  TEXT,
    detail     TEXT,
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS query_log (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id),
    dept_code     TEXT,
    query_text    TEXT,
    response_ms   INTEGER,
    faithfulness  REAL,
    sources_count INTEGER DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS token_blacklist (
    jti        TEXT PRIMARY KEY,
    expired_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_department       ON users(department);
CREATE INDEX IF NOT EXISTS idx_users_role             ON users(role);
CREATE INDEX IF NOT EXISTS idx_query_log_dept         ON query_log(dept_code);
CREATE INDEX IF NOT EXISTS idx_query_log_created      ON query_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_log_user         ON query_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_dept         ON audit_log(dept_code);
CREATE INDEX IF NOT EXISTS idx_audit_log_created      ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_access_requests_dept   ON access_requests(dept_code);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_exp    ON token_blacklist(expired_at)
"""


def run():
    if not PG_URL:
        print("ERROR: Set DATABASE_URL environment variable")
        print("Example: export DATABASE_URL=postgresql://huron_user:HuronDB2026!@localhost:5436/huron")
        sys.exit(1)

    if not SQLITE_PATH.exists():
        print(f"ERROR: SQLite DB not found at {SQLITE_PATH}")
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print("ERROR: pip install psycopg2-binary")
        sys.exit(1)

    print(f"[1/4] Connecting to SQLite: {SQLITE_PATH}")
    sq = sqlite3.connect(SQLITE_PATH)
    sq.row_factory = sqlite3.Row

    print(f"[2/4] Connecting to PostgreSQL: {PG_URL[:50]}...")
    pg = psycopg2.connect(PG_URL)
    pg.autocommit = False
    cur = pg.cursor()

    print("[3/4] Creating PostgreSQL schema...")
    for stmt in PG_SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt + ";")
    pg.commit()

    print("[4/4] Migrating data...")
    for table in TABLES:
        try:
            rows = sq.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
        except Exception as e:
            print(f"  {table}: skipped ({e})")
            continue

        if not rows:
            print(f"  {table}: empty, skipping")
            continue

        cols = list(rows[0].keys())
        placeholders = ",".join(["%s"] * len(cols))
        col_list = ",".join(cols)
        insert = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"  # noqa: S608

        bool_cols = BOOL_COLS.get(table, set())

        def coerce(col, val):
            if col in bool_cols and isinstance(val, int):
                return bool(val)
            return val

        count = 0
        for row in rows:
            cur.execute(insert, [coerce(c, row[c]) for c in cols])
            count += 1
        pg.commit()
        print(f"  {table}: {count} rows migrated")

    # Reset sequences so next INSERT gets the right id
    for table in ["users", "departments", "access_requests", "audit_log", "query_log"]:
        cur.execute(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 1))")  # noqa: S608
    pg.commit()

    print("\nMigration complete.")
    print("\nNext steps:")
    print("  1. Set DATABASE_URL in your .env file")
    print("  2. Restart the backend — it will connect to PostgreSQL automatically")

    sq.close()
    pg.close()


if __name__ == "__main__":
    run()
