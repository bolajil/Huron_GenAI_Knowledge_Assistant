"""
Dev / Staging seed data.
Creates test users and sample queries so every cloud environment
starts with a consistent, testable base state.

Run after migrations:
    python -m migrations.seed_dev            # insert if not exists
    python -m migrations.seed_dev --reset    # wipe test data and re-insert

NEVER run against production.
"""
import os, sys, argparse, logging
import bcrypt
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
APP_ENV      = os.environ.get("APP_ENV", "dev")

# ── Safety guard ──────────────────────────────────────────────────────────────
if APP_ENV == "prod":
    log.error("seed_dev must NOT run in production (APP_ENV=prod). Aborting.")
    sys.exit(1)

TEST_USERS = [
    {
        "username": "hr_admin",
        "email": "hr.admin@huron-test.ai",
        "full_name": "HR Department Admin",
        "password": "HuronHR2026!",
        "role": "dept_admin",
        "department": "hr",
    },
    {
        "username": "legal_user",
        "email": "legal.user@huron-test.ai",
        "full_name": "Legal Team Member",
        "password": "HuronLegal2026!",
        "role": "user",
        "department": "legal",
    },
    {
        "username": "it_engineer",
        "email": "it.engineer@huron-test.ai",
        "full_name": "IT Engineer",
        "password": "HuronIT2026!",
        "role": "user",
        "department": "it",
    },
]

SAMPLE_QUERIES = [
    ("hr",    "What is the PTO policy for new employees?"),
    ("legal", "What are the HIPAA compliance requirements for PHI handling?"),
    ("hr",    "How do we handle performance improvement plans?"),
    ("it",    "What is the approved software installation process?"),
]


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(DATABASE_URL)


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def run(reset=False):
    conn = get_conn()
    cur  = conn.cursor()

    try:
        if reset:
            log.info("Resetting test data...")
            cur.execute(
                "DELETE FROM users WHERE email LIKE '%@huron-test.ai'"
            )
            conn.commit()
            log.info("Test users removed")

        # Insert test users
        inserted = 0
        for u in TEST_USERS:
            cur.execute("SELECT id FROM users WHERE username=%s", (u["username"],))
            if not cur.fetchone():
                cur.execute(
                    """INSERT INTO users
                       (username, email, full_name, password_hash, role, department)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (u["username"], u["email"], u["full_name"],
                     hash_pw(u["password"]), u["role"], u["department"])
                )
                inserted += 1
                log.info("Created user: %s (%s)", u["username"], u["role"])

        # Insert sample queries linked to root user
        cur.execute("SELECT id FROM users WHERE username='root'")
        row = cur.fetchone()
        if row:
            root_id = row[0]
            for dept, query_text in SAMPLE_QUERIES:
                cur.execute(
                    """INSERT INTO queries (user_id, department, query_text, response_time_ms)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT DO NOTHING""",
                    (root_id, dept, query_text, 0)
                )

        conn.commit()
        log.info("Seed complete — %d user(s) inserted", inserted)

        # Print summary
        cur.execute("SELECT COUNT(*) FROM users")
        log.info("Total users: %d", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM departments")
        log.info("Total departments: %d", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM queries")
        log.info("Total queries: %d", cur.fetchone()[0])

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Remove and re-insert test data")
    args = parser.parse_args()
    run(reset=args.reset)
