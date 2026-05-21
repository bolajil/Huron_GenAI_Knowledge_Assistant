"""
One-time migration: SQLite (data/huron.db) → PostgreSQL.

Usage:
  python migrate_sqlite_to_postgres.py --pg-dsn "postgresql://user:pass@host:5432/huron"

Requirements:
  pip install psycopg2-binary
"""

import argparse
import sqlite3
import sys
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    sys.exit("psycopg2-binary not installed.  Run: pip install psycopg2-binary")

SQLITE_PATH = Path(__file__).parent / "data" / "huron.db"

# ── PostgreSQL DDL ──────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS departments (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    namespace   TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    full_name       TEXT,
    hashed_password TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'user',
    department_id   INTEGER REFERENCES departments(id),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    mfa_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    filename        TEXT NOT NULL,
    department_id   INTEGER REFERENCES departments(id),
    uploaded_by     INTEGER REFERENCES users(id),
    sensitivity     TEXT NOT NULL DEFAULT 'internal',
    pinecone_ids    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS query_log (
    id               SERIAL PRIMARY KEY,
    user_id          INTEGER REFERENCES users(id),
    query_text       TEXT NOT NULL,
    department_id    INTEGER REFERENCES departments(id),
    response_time_ms REAL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS access_requests (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    requested_dept  TEXT NOT NULL,
    requested_role  TEXT NOT NULL,
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    reviewed_by     INTEGER REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jwt_blacklist (
    id         SERIAL PRIMARY KEY,
    jti        TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_users_username        ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email           ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_department_id   ON users(department_id);
CREATE INDEX IF NOT EXISTS idx_users_role            ON users(role);
CREATE INDEX IF NOT EXISTS idx_query_log_user_id     ON query_log(user_id);
CREATE INDEX IF NOT EXISTS idx_query_log_dept_id     ON query_log(department_id);
CREATE INDEX IF NOT EXISTS idx_query_log_created_at  ON query_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jwt_blacklist_jti     ON jwt_blacklist(jti);
CREATE INDEX IF NOT EXISTS idx_jwt_blacklist_expires ON jwt_blacklist(expires_at);
CREATE INDEX IF NOT EXISTS idx_access_requests_user  ON access_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_access_requests_status ON access_requests(status);
"""


def migrate(pg_dsn: str, dry_run: bool = False) -> None:
    if not SQLITE_PATH.exists():
        sys.exit(f"SQLite DB not found at {SQLITE_PATH}")

    sq = sqlite3.connect(SQLITE_PATH)
    sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(pg_dsn)
    pg.autocommit = False
    cur = pg.cursor()

    print("Creating PostgreSQL schema…")
    cur.execute(SCHEMA_SQL)

    tables = [
        "departments",
        "users",
        "documents",
        "query_log",
        "access_requests",
        "jwt_blacklist",
    ]

    for table in tables:
        rows = sq.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608 — internal migration, not user input
        if not rows:
            print(f"  {table}: empty, skipping")
            continue

        cols = rows[0].keys()
        placeholders = ", ".join(["%s"] * len(cols))
        col_names = ", ".join(cols)
        insert_sql = f'INSERT INTO {table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'

        data = [tuple(row) for row in rows]
        print(f"  {table}: migrating {len(data)} rows…")
        if not dry_run:
            psycopg2.extras.execute_batch(cur, insert_sql, data, page_size=500)

    # Reset sequences to max(id) + 1 so INSERT without explicit id works
    if not dry_run:
        for table in tables:
            try:
                cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 0) + 1, false) FROM {table}")  # noqa: S608
            except psycopg2.Error:
                pass  # table has no serial id column

        pg.commit()
        print("Migration committed.")
    else:
        pg.rollback()
        print("Dry run — no changes committed.")

    sq.close()
    pg.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite → PostgreSQL")
    parser.add_argument("--pg-dsn", required=True, help="PostgreSQL DSN, e.g. postgresql://user:pass@host:5432/huron")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    args = parser.parse_args()
    migrate(args.pg_dsn, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
