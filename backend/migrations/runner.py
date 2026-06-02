"""
Database migration runner.
Tracks applied migrations in a schema_migrations table.
Safe to run on every deploy — skips already-applied migrations.

Usage:
    python -m migrations.runner                    # run all pending
    python -m migrations.runner --dry-run          # show what would run
"""
import os, sys, argparse, logging
from pathlib import Path
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "versions"
DATABASE_URL   = os.environ.get("DATABASE_URL", "")


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)


def ensure_migrations_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id          SERIAL PRIMARY KEY,
            version     TEXT NOT NULL UNIQUE,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def applied_versions(cur) -> set:
    cur.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cur.fetchall()}


def pending_migrations(applied: set) -> list[Path]:
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    return [f for f in files if f.stem not in applied]


def run(dry_run=False):
    conn = get_conn()
    conn.autocommit = False
    cur  = conn.cursor()

    try:
        ensure_migrations_table(cur)
        conn.commit()

        applied = applied_versions(cur)
        pending = pending_migrations(applied)

        if not pending:
            log.info("Database is up to date — no migrations to run")
            return

        for path in pending:
            log.info("Migration: %s %s", path.stem, "(dry-run)" if dry_run else "")
            if not dry_run:
                sql = path.read_text(encoding="utf-8")
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (path.stem,)
                )
                conn.commit()
                log.info("Applied: %s", path.stem)

        log.info("Done — %d migration(s) applied", len(pending))

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
