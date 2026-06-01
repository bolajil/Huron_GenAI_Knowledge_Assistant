"""
Huron GenAI Knowledge Assistant — FastAPI Backend v4
All frontend/backend integration gaps fixed:
  1. Added /api/v1/dept-admin/users aliases (GET + POST)
  2. Added PATCH /api/v1/root/users/{id} (was PUT only)
  3. Fixed access-requests status filter param: status_filter → status
  4. Stats response includes all fields frontend expects
  5. Graceful degraded mode when utils/ pipeline modules missing
  6. PostgreSQL migration path documented inline
"""

from __future__ import annotations

import asyncio, os, sys, sqlite3, logging, secrets, time, json, hashlib, base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
import uvicorn
from dotenv import load_dotenv
from fastapi import (
    FastAPI, Depends, HTTPException, UploadFile,
    File, Form, status, Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

# Load shared API keys from the project root first, then let backend/.env
# override backend-specific settings (SENTRY_DSN, APP_ENV, JWT_SECRET_KEY).
# Root goes first so its real values win before backend/.env can shadow them
# with empty placeholder lines.
_ROOT_DIR = Path(__file__).parent.parent
load_dotenv(_ROOT_DIR / ".env",             override=False)
load_dotenv(_ROOT_DIR / "backend" / ".env", override=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))  # makes agent/ importable

# ─── Sentry Error Tracking ────────────────────────────────────────────────────
# No-op when SENTRY_DSN is blank — safe to leave empty during development.
_SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if _SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        def _scrub_sentry_event(event, hint):  # noqa: ANN001
            """Remove sensitive fields before sending to Sentry."""
            req = event.get("request", {})
            if "data" in req and isinstance(req["data"], dict):
                for field in ("query", "content", "messages", "password", "token"):
                    if field in req["data"]:
                        req["data"][field] = "[Filtered]"
            headers = req.get("headers", {})
            headers.pop("authorization", None)
            headers.pop("cookie", None)
            return event

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            environment=os.getenv("APP_ENV", "development"),
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            # Capture 20% of requests for performance tracing.
            # Set to 1.0 temporarily when diagnosing slow endpoints.
            traces_sample_rate=0.2,
            before_send=_scrub_sentry_event,
        )
        logger.info("Sentry initialised (env=%s)", os.getenv("APP_ENV", "development"))
    except ImportError:
        logger.warning("sentry-sdk not installed — run: pip install sentry-sdk[fastapi]")

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(title="Huron GenAI API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:3001",
        "http://127.0.0.1:3000", "http://127.0.0.1:3001",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SECRET_KEY  = os.getenv("JWT_SECRET_KEY", "huron-change-this-in-production")
ALGORITHM   = "HS256"
TOKEN_HOURS = 8

# ─── MCP credential encryption ────────────────────────────────────────────────
# Uses MCP_ENCRYPTION_KEY when set (recommended for production so JWT rotation
# doesn't invalidate stored tool credentials).  Falls back to JWT-derived key
# for zero-config local dev.
from cryptography.fernet import Fernet as _Fernet  # cryptography already in requirements

_MCP_ENC_KEY = os.getenv("MCP_ENCRYPTION_KEY", "")

def _fernet() -> _Fernet:
    if _MCP_ENC_KEY:
        # Caller must supply a valid 32-byte URL-safe base64 key.
        raw = hashlib.sha256(_MCP_ENC_KEY.encode()).digest()
    else:
        raw = hashlib.sha256(SECRET_KEY.encode()).digest()
    return _Fernet(base64.urlsafe_b64encode(raw))

def _encrypt_config(cfg: dict) -> str:
    return _fernet().encrypt(json.dumps(cfg).encode()).decode()

def _decrypt_config(ciphertext: str) -> dict:
    return json.loads(_fernet().decrypt(ciphertext.encode()))

# ─── Database ────────────────────────────────────────────────────────────────
#
# POSTGRESQL MIGRATION — run when ready:
#   pip install asyncpg sqlalchemy[asyncio]
#   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/huron"
#   Replace db_conn() with SQLAlchemy async session + Alembic.
#   Connection pool: pool_size=20, max_overflow=40, pool_timeout=30
#   PgBouncer in front for 20k users (transaction pooling mode).
#
_default_db  = str(Path(__file__).parent / "data" / "huron.db")
DB_PATH      = Path(os.getenv("SQLITE_DB_PATH", _default_db))
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:                                   # SQLite only — skip in PostgreSQL mode
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# VECTOR_BACKEND: "pinecone" (default when PINECONE_API_KEY is set) or "faiss"
# (local dev / CI without a Pinecone account).  Consumed by utils/ pipeline.
VECTOR_BACKEND = os.getenv(
    "VECTOR_BACKEND",
    "pinecone" if os.getenv("PINECONE_API_KEY") else "faiss",
)
os.environ.setdefault("VECTOR_BACKEND", VECTOR_BACKEND)  # expose to child modules

# Token blacklist — in-memory (dev) or Redis (production).
# Set REDIS_URL=redis://host:6379/0 to activate Redis-backed blacklist.
# Without REDIS_URL the previous in-memory + SQLite behaviour is preserved.
_token_blacklist: set[str] = set()

_REDIS_URL = os.getenv("REDIS_URL", "")
_redis_client = None
if _REDIS_URL:
    try:
        import redis as _redis_lib
        _redis_client = _redis_lib.from_url(_REDIS_URL, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis JWT blacklist active: %s", _REDIS_URL.split("@")[-1])
    except Exception as _re:
        logger.warning("Redis unavailable (%s) — falling back to in-memory blacklist", _re)
        _redis_client = None


class _DBConn:
    """Thin adapter — presents a sqlite3-like execute() interface over psycopg2 or sqlite3."""

    def __init__(self):
        if DATABASE_URL:
            import psycopg2
            import psycopg2.extras
            self._raw   = psycopg2.connect(DATABASE_URL)
            self._cur   = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            self._is_pg = True
        else:
            self._raw   = sqlite3.connect(DB_PATH)
            self._raw.row_factory = sqlite3.Row
            self._is_pg = False

    def execute(self, sql: str, params=()):
        if self._is_pg:
            sql = sql.replace("?", "%s")
            if "INSERT OR IGNORE" in sql:
                sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO")
                sql = sql.rstrip("; ") + " ON CONFLICT DO NOTHING"
            # Boolean column literals: PostgreSQL BOOLEAN rejects integer comparisons
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


def _ensure_pg_feedback_table():
    """Create feedback_log in PostgreSQL if it does not exist (safe to run every startup)."""
    if not DATABASE_URL:
        return
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback_log (
                id         SERIAL PRIMARY KEY,
                user_id    INTEGER REFERENCES users(id),
                username   TEXT,
                dept_code  TEXT,
                query_text TEXT,
                response   TEXT,
                source     TEXT,
                rating     INTEGER NOT NULL,
                comment    TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Could not ensure feedback_log table: %s", exc)


def _seed_db():
    """Ensure root user and departments exist — works for both SQLite and PostgreSQL."""
    _DEPTS = [
        ("hr",         "Human Resources",  "vaultmind-huron-hr-general",         "confidential"),
        ("legal",      "Legal",            "vaultmind-huron-legal-general",       "restricted"),
        ("finance",    "Finance",          "vaultmind-huron-finance-general",     "restricted"),
        ("clinical",   "Clinical",         "vaultmind-huron-clinical-general",    "hipaa_phi"),
        ("operations", "Operations",       "vaultmind-huron-operations-general",  "internal"),
        ("it",         "IT & Engineering", "vaultmind-huron-it-general",          "confidential"),
        ("marketing",  "Marketing",        "vaultmind-huron-marketing-general",   "internal"),
        ("external",   "External Sources", "vaultmind-huron-external-general",    "public"),
    ]
    with _DBConn() as conn:
        if not conn.execute("SELECT id FROM users WHERE role=?", ("root",)).fetchone():
            ph = bcrypt.hashpw(b"HuronRoot2026!", bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username,email,full_name,password_hash,role,department) "
                "VALUES (?,?,?,?,?,?)",
                ("root", "root@huron-vaultmind.ai", "Root Administrator", ph, "root", "all"),
            )
            logger.info("Root user created — username: root  password: HuronRoot2026!")
        for code, name, ns, cls in _DEPTS:
            if not conn.execute("SELECT id FROM departments WHERE code=?", (code,)).fetchone():
                conn.execute(
                    "INSERT INTO departments (code,display_name,namespace,classification) VALUES (?,?,?,?)",
                    (code, name, ns, cls),
                )
        conn.commit()


def _ensure_pg_agent_runs_table():
    """Create agent_runs table in PostgreSQL if missing."""
    try:
        conn = _DBConn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_runs (
                id                  TEXT PRIMARY KEY,
                user_id             INTEGER,
                dept                TEXT,
                query               TEXT,
                status              TEXT DEFAULT 'running',
                steps               TEXT,
                final_answer        TEXT,
                namespaces_accessed TEXT,
                steps_taken         INTEGER DEFAULT 0,
                model               TEXT,
                created_at          TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Could not ensure agent_runs table: %s", exc)


def _ensure_pg_doc_versions_table():
    """Create document_versions table in PostgreSQL if missing."""
    try:
        conn = _DBConn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS document_versions (
                id             SERIAL PRIMARY KEY,
                dept           TEXT NOT NULL,
                doc_id         TEXT NOT NULL,
                version        TEXT NOT NULL,
                source_file    TEXT NOT NULL,
                file_type      TEXT NOT NULL DEFAULT 'unknown',
                effective_date TEXT,
                vector_ids     TEXT,
                chunk_count    INTEGER DEFAULT 0,
                is_latest      INTEGER DEFAULT 1,
                ingested_by    TEXT,
                ingested_at    TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(dept, doc_id, version)
            )
        """)
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Could not ensure document_versions table: %s", exc)


def _ensure_pg_conversations_tables():
    """Create conversations + conversation_messages tables in PostgreSQL if missing."""
    if not DATABASE_URL:
        return
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id         TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                dept       TEXT NOT NULL DEFAULT 'general',
                tab        TEXT NOT NULL DEFAULT 'chat',
                title      TEXT NOT NULL DEFAULT 'New Conversation',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id              SERIAL PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content         TEXT NOT NULL,
                source          TEXT,
                source_label    TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_user
            ON conversations(user_id, updated_at DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_msg
            ON conversation_messages(conversation_id, created_at ASC)
        """)
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Could not ensure conversations tables: %s", exc)


def _ensure_pg_mcp_tables():
    """Create mcp_tools, mcp_tool_configs, mcp_action_log in PostgreSQL if missing."""
    try:
        conn = _DBConn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mcp_tools (
                id          SERIAL PRIMARY KEY,
                name        TEXT NOT NULL,
                category    TEXT NOT NULL DEFAULT 'communication',
                description TEXT NOT NULL DEFAULT '',
                tool_type   TEXT NOT NULL,
                dept_scope  TEXT,
                min_role    TEXT NOT NULL DEFAULT 'user',
                is_enabled  INTEGER NOT NULL DEFAULT 1,
                created_by  TEXT NOT NULL DEFAULT 'system',
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mcp_tool_configs (
                id            SERIAL PRIMARY KEY,
                tool_id       INTEGER NOT NULL REFERENCES mcp_tools(id) ON DELETE CASCADE,
                dept_code     TEXT NOT NULL,
                config_json   TEXT NOT NULL,
                configured_by TEXT NOT NULL DEFAULT 'system',
                configured_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(tool_id, dept_code)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mcp_action_log (
                id            SERIAL PRIMARY KEY,
                tool_id       INTEGER REFERENCES mcp_tools(id),
                user_id       INTEGER REFERENCES users(id),
                dept_code     TEXT,
                query_snippet TEXT,
                status        TEXT NOT NULL DEFAULT 'ok',
                error_msg     TEXT,
                ran_at        TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Could not ensure mcp tables: %s", exc)


def _ensure_pg_core_tables():
    """Create base schema in PostgreSQL (users, departments, etc.) if missing."""
    try:
        conn = _DBConn()
        conn.execute("""
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
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id              SERIAL PRIMARY KEY,
                code            TEXT UNIQUE NOT NULL,
                display_name    TEXT NOT NULL,
                namespace       TEXT UNIQUE NOT NULL,
                classification  TEXT NOT NULL DEFAULT 'internal',
                is_active       BOOLEAN NOT NULL DEFAULT TRUE,
                admin_user_id   INTEGER REFERENCES users(id),
                doc_count       INTEGER NOT NULL DEFAULT 0,
                query_count     INTEGER NOT NULL DEFAULT 0,
                user_count      INTEGER NOT NULL DEFAULT 0,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS access_requests (
                id              SERIAL PRIMARY KEY,
                requester_id    INTEGER NOT NULL REFERENCES users(id),
                dept_code       TEXT NOT NULL,
                requested_tab   TEXT NOT NULL,
                requested_role  TEXT NOT NULL DEFAULT 'user',
                justification   TEXT NOT NULL DEFAULT '',
                status          TEXT NOT NULL DEFAULT 'pending',
                reviewed_by     INTEGER REFERENCES users(id),
                reviewed_at     TIMESTAMPTZ,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id          SERIAL PRIMARY KEY,
                user_id     INTEGER REFERENCES users(id),
                username    TEXT,
                action      TEXT NOT NULL,
                dept_code   TEXT,
                namespace   TEXT,
                detail      TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id            SERIAL PRIMARY KEY,
                user_id       INTEGER REFERENCES users(id),
                dept_code     TEXT,
                query_text    TEXT,
                response_ms   INTEGER,
                faithfulness  REAL,
                sources_count INTEGER DEFAULT 0,
                created_at    TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS token_blacklist (
                jti        TEXT PRIMARY KEY,
                expired_at TIMESTAMPTZ NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS oidc_role_mappings (
                id           SERIAL PRIMARY KEY,
                ad_group     TEXT NOT NULL UNIQUE,
                huron_role   TEXT NOT NULL CHECK(huron_role IN ('root','dept_admin','power_user','user')),
                dept_code    TEXT,
                description  TEXT,
                created_by   TEXT NOT NULL DEFAULT 'system',
                created_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("Could not ensure core tables: %s", exc)
        raise  # re-raise so init_db() fails fast rather than proceeding to _seed_db()


def _seed_mcp_tools():
    """Insert the four default MCP tools if the table is empty."""
    _DEFAULTS = [
        ("Slack Notification", "communication", "Send result to a Slack channel",      "slack",         None, "user"),
        ("Email Report",       "communication", "Email result to a recipient",          "email",         None, "user"),
        ("PDF Report",         "report",        "Download result as a formatted PDF",   "pdf_report",    None, "user"),
        ("Data Analyzer",      "analysis",      "AI analysis of trends in the result",  "data_analyzer", None, "power_user"),
    ]
    try:
        with _DBConn() as conn:
            if conn.execute("SELECT id FROM mcp_tools LIMIT 1").fetchone():
                return
            for name, cat, desc, ttype, scope, min_role in _DEFAULTS:
                conn.execute(
                    "INSERT INTO mcp_tools (name,category,description,tool_type,dept_scope,min_role) "
                    "VALUES (?,?,?,?,?,?)",
                    (name, cat, desc, ttype, scope, min_role),
                )
            conn.commit()
    except Exception as exc:
        logger.warning("Could not seed mcp_tools: %s", exc)


def init_db():
    if DATABASE_URL:
        _ensure_pg_core_tables()           # base schema first — users, departments, etc.
        _ensure_pg_feedback_table()
        _ensure_pg_agent_runs_table()
        _ensure_pg_doc_versions_table()
        _ensure_pg_conversations_tables()
        _ensure_pg_mcp_tables()
        _seed_db()                         # seed after all tables exist
        _seed_mcp_tools()
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            full_name     TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'user',
            department    TEXT NOT NULL DEFAULT 'general',
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_by    INTEGER REFERENCES users(id),
            last_login    TIMESTAMP,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            code            TEXT UNIQUE NOT NULL,
            display_name    TEXT NOT NULL,
            namespace       TEXT UNIQUE NOT NULL,
            classification  TEXT NOT NULL DEFAULT 'internal',
            is_active       INTEGER NOT NULL DEFAULT 1,
            admin_user_id   INTEGER REFERENCES users(id),
            doc_count       INTEGER NOT NULL DEFAULT 0,
            query_count     INTEGER NOT NULL DEFAULT 0,
            user_count      INTEGER NOT NULL DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS access_requests (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id    INTEGER NOT NULL REFERENCES users(id),
            dept_code       TEXT NOT NULL,
            requested_tab   TEXT NOT NULL,
            requested_role  TEXT NOT NULL DEFAULT 'user',
            justification   TEXT NOT NULL DEFAULT '',
            status          TEXT NOT NULL DEFAULT 'pending',
            reviewed_by     INTEGER REFERENCES users(id),
            reviewed_at     TIMESTAMP,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            username    TEXT,
            action      TEXT NOT NULL,
            dept_code   TEXT,
            namespace   TEXT,
            detail      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS query_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER REFERENCES users(id),
            dept_code     TEXT,
            query_text    TEXT,
            response_ms   INTEGER,
            faithfulness  REAL,
            sources_count INTEGER DEFAULT 0,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            jti        TEXT PRIMARY KEY,
            expired_at TIMESTAMP NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            username    TEXT,
            dept_code   TEXT,
            query_text  TEXT,
            response    TEXT,
            source      TEXT,
            rating      INTEGER NOT NULL,
            comment     TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_runs (
            id                  TEXT PRIMARY KEY,
            user_id             INTEGER REFERENCES users(id),
            dept                TEXT,
            query               TEXT,
            status              TEXT DEFAULT 'running',
            steps               TEXT,
            final_answer        TEXT,
            namespaces_accessed TEXT,
            steps_taken         INTEGER DEFAULT 0,
            model               TEXT,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_versions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            dept           TEXT NOT NULL,
            doc_id         TEXT NOT NULL,
            version        TEXT NOT NULL,
            source_file    TEXT NOT NULL,
            file_type      TEXT NOT NULL DEFAULT 'unknown',
            effective_date TEXT,
            vector_ids     TEXT,
            chunk_count    INTEGER DEFAULT 0,
            is_latest      INTEGER DEFAULT 1,
            ingested_by    TEXT,
            ingested_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dept, doc_id, version)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id         TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            dept       TEXT NOT NULL DEFAULT 'general',
            tab        TEXT NOT NULL DEFAULT 'chat',
            title      TEXT NOT NULL DEFAULT 'New Conversation',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role            TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
            content         TEXT NOT NULL,
            source          TEXT,
            source_label    TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conv_user
        ON conversations(user_id, updated_at DESC)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conv_msg
        ON conversation_messages(conversation_id, created_at ASC)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mcp_tools (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL DEFAULT 'communication',
            description TEXT NOT NULL DEFAULT '',
            tool_type   TEXT NOT NULL,
            dept_scope  TEXT,
            min_role    TEXT NOT NULL DEFAULT 'user',
            is_enabled  INTEGER NOT NULL DEFAULT 1,
            created_by  TEXT NOT NULL DEFAULT 'system',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mcp_tool_configs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id       INTEGER NOT NULL REFERENCES mcp_tools(id) ON DELETE CASCADE,
            dept_code     TEXT NOT NULL,
            config_json   TEXT NOT NULL,
            configured_by TEXT NOT NULL DEFAULT 'system',
            configured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tool_id, dept_code)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mcp_action_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_id       INTEGER REFERENCES mcp_tools(id),
            user_id       INTEGER REFERENCES users(id),
            dept_code     TEXT,
            query_snippet TEXT,
            status        TEXT NOT NULL DEFAULT 'ok',
            error_msg     TEXT,
            ran_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS oidc_role_mappings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_group     TEXT NOT NULL UNIQUE,
            huron_role   TEXT NOT NULL CHECK(huron_role IN ('root','dept_admin','power_user','user')),
            dept_code    TEXT,
            description  TEXT,
            created_by   TEXT NOT NULL DEFAULT 'system',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    _seed_db()
    _seed_mcp_tools()
    _ensure_pg_feedback_table()
    _ensure_pg_agent_runs_table()
    _ensure_pg_doc_versions_table()


# ─── DB helpers ───────────────────────────────────────────────────────────────

def db_conn():
    return _DBConn()


def get_user_by_id(uid: int) -> Optional[dict]:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,username,email,full_name,role,department,is_active FROM users WHERE id=?",
            (uid,),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_login(username: str) -> Optional[dict]:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,username,email,full_name,password_hash,role,department,is_active "
            "FROM users WHERE username=? OR email=?",
            (username, username),
        ).fetchone()
    return dict(row) if row else None


def write_audit(uid, uname: str, action: str, dept="", ns="", detail=""):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (user_id,username,action,dept_code,namespace,detail) VALUES (?,?,?,?,?,?)",
            (uid, uname, action, dept, ns, detail),
        )
        conn.commit()


def log_query(uid: int, dept: str, text: str, ms: int, faith: float, srcs: int):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO query_log (user_id,dept_code,query_text,response_ms,faithfulness,sources_count) "
            "VALUES (?,?,?,?,?,?)",
            (uid, dept, text[:500], ms, faith, srcs),
        )
        conn.execute("UPDATE departments SET query_count=query_count+1 WHERE code=?", (dept,))
        conn.commit()


# ─── Role definitions ─────────────────────────────────────────────────────────

ROLE_CLEARANCE = {"root": 5, "dept_admin": 4, "power_user": 3, "user": 2, "viewer": 1}

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "root":       ["query","chat","ingest","research","agent","cross_dept_query","admin",
                   "manage_users","manage_departments","manage_all_depts","create_dept_admin",
                   "approve_requests","view_audit_log","mcp","analytics"],
    "dept_admin": ["query","chat","ingest","research","agent","manage_users",
                   "manage_dept_users","approve_requests","analytics","mcp"],
    "power_user": ["query","chat","ingest","research","agent","cross_dept_query","analytics"],
    "user":       ["query","chat","ingest"],
    "viewer":     ["query","chat"],
}


def _ns_scope(role: str, dept: str) -> list[str]:
    return ["*"] if role == "root" else [dept]


def create_token(user: dict) -> str:
    jti    = secrets.token_hex(16)
    expire = datetime.utcnow() + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({
        "jti": jti,
        "sub": user["username"],
        "user_id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name") or user["username"].title(),
        "role": user["role"],
        "dept_id": user["department"],
        "clearance_level": ROLE_CLEARANCE.get(user["role"], 1),
        "namespace_scope": _ns_scope(user["role"], user["department"]),
        "permissions": ROLE_PERMISSIONS.get(user["role"], ["query","chat"]),
        "exp": expire,
        "iat": datetime.utcnow(),
    }, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti", "")
        if _redis_client:
            if _redis_client.sismember("huron:blacklist", jti):
                return None
        else:
            if jti in _token_blacklist:
                return None
            with db_conn() as conn:
                if conn.execute("SELECT jti FROM token_blacklist WHERE jti=?", (jti,)).fetchone():
                    _token_blacklist.add(jti)
                    return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def blacklist_token(token: str):
    try:
        p   = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        jti = p.get("jti", "")
        exp = datetime.utcfromtimestamp(p.get("exp", 0))
        ttl = max(int((exp - datetime.utcnow()).total_seconds()), 1)
        if _redis_client:
            _redis_client.sadd("huron:blacklist", jti)
            # expire the set member after the token's natural lifetime
            _redis_client.expire("huron:blacklist", ttl + 3600)
        else:
            _token_blacklist.add(jti)
            with db_conn() as conn:
                conn.execute("INSERT OR IGNORE INTO token_blacklist (jti,expired_at) VALUES (?,?)", (jti, exp))
                conn.commit()
    except Exception:
        pass


# ─── Dependencies ─────────────────────────────────────────────────────────────

async def current_user(token: str = Depends(oauth2_scheme)) -> dict:
    p = verify_token(token)
    if not p:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return p


async def require_root(p: dict = Depends(current_user)) -> dict:
    if p.get("role") != "root":
        raise HTTPException(status_code=403, detail="Root access required")
    return p


async def require_admin(p: dict = Depends(current_user)) -> dict:
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return p


def perm(p: dict, name: str):
    if name not in p.get("permissions", []):
        raise HTTPException(status_code=403, detail=f"Permission '{name}' required")


def dept_gate(p: dict, target: str):
    """Enforce Pinecone namespace isolation at the API layer."""
    role  = p.get("role")
    udept = p.get("dept_id")
    scope = p.get("namespace_scope", [])
    if role == "root" or "*" in scope:
        return
    if udept != target and target not in scope:
        write_audit(p.get("user_id"), p.get("sub"), "namespace_access_denied",
                    target, target, f"dept={udept} tried to access dept={target}")
        raise HTTPException(
            status_code=403,
            detail=f"Access to department '{target}' is not permitted for your account",
        )


# ─── Pipeline singletons (graceful degraded when utils/ empty) ────────────────

_svc = None
_rag = None


def get_svc():
    global _svc
    if _svc is None:
        try:
            from utils.ingestion_service import IngestionService
            _svc = IngestionService(
                enable_pinecone=True,
                enable_dlp_scan=True,
                enable_quality_gate=True,
                enable_classification=False,
                pinecone_index=os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge"),
            )
        except Exception as e:
            logger.warning(f"IngestionService unavailable: {e}")
    return _svc


def get_rag():
    global _rag
    if _rag is None:
        try:
            from utils.rag_orchestrator import RAGOrchestrator
            _rag = RAGOrchestrator(
                pinecone_index=os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge"),
            )
        except Exception as e:
            logger.warning(f"RAGOrchestrator unavailable: {e}")
    return _rag


# ─── Pydantic models ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str
    auth_method: str = "local"
    remember_me: bool = False


class CreateUserRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: str = "user"
    department: str


class UpdateUserRequest(BaseModel):
    full_name:  Optional[str]  = None
    role:       Optional[str]  = None
    department: Optional[str]  = None
    is_active:  Optional[bool] = None


class QueryRequest(BaseModel):
    query:      str
    department: Optional[str] = None
    top_k:      int = 10


class ChatRequest(BaseModel):
    messages:   list[dict]
    department: Optional[str] = None


class AccessRequestCreate(BaseModel):
    dept_code:      str
    requested_tab:  str
    requested_role: str = "user"
    justification:  str


class AccessRequestReview(BaseModel):
    request_id: int
    action:     str
    note:       Optional[str] = None


class FeedbackRequest(BaseModel):
    query:     str
    response:  str
    rating:    int          # 1 = thumbs up, -1 = thumbs down
    source:    str = "rag"  # "rag" | "general_knowledge"
    dept_code: str = "general"
    comment:   Optional[str] = None


class AgentRunRequest(BaseModel):
    query:     str
    dept:      Optional[str] = None
    model:     str = "gpt-4o-mini"
    max_steps: int = 12


class ResearchRequest(BaseModel):
    query:           str
    use_internal:    bool = True
    use_web:         bool = True
    use_cross_dept:  bool = False
    use_ai_analysis: bool = True
    dept:            Optional[str] = None


class ConversationCreate(BaseModel):
    tab:   str = "chat"        # "chat" | "query" | "agent"
    dept:  Optional[str] = None
    title: str = "New Conversation"


class MessageAppend(BaseModel):
    role:         str            # "user" | "assistant"
    content:      str
    source:       Optional[str] = None
    source_label: Optional[str] = None


# ─── Simple in-memory query-result cache ─────────────────────────────────────
import hashlib as _hashlib, time as _time

_query_cache: dict = {}          # key → {"result": ..., "expires": float}
CACHE_TTL_SECONDS = 300          # 5 minutes


def _cache_key(dept: str, query: str) -> str:
    return _hashlib.sha256(f"{dept}:{query.strip().lower()}".encode()).hexdigest()[:16]


def _cache_get(dept: str, query: str):
    entry = _query_cache.get(_cache_key(dept, query))
    if entry and entry["expires"] > _time.time():
        return entry["result"]
    return None


def _cache_set(dept: str, query: str, result: dict):
    if len(_query_cache) > 500:          # cap size in dev
        oldest = min(_query_cache, key=lambda k: _query_cache[k]["expires"])
        _query_cache.pop(oldest, None)
    _query_cache[_cache_key(dept, query)] = {
        "result":  result,
        "expires": _time.time() + CACHE_TTL_SECONDS,
    }


# In-memory stores for active agent runs (replace with Redis for multi-worker)
_active_runs: dict = {}   # run_id → ReActAgent
_run_steps:   dict = {}   # run_id → list[dict]


# ─── Startup ─────────────────────────────────────────────────────────────────
init_db()


# ═════════════════════════════════════════════════════════════════════════════
# AUTH
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/auth/login")
async def login(req: LoginRequest):
    user = get_user_by_login(req.username)
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
        write_audit(None, req.username, "auth_failure")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user)
    write_audit(user["id"], user["username"], "login")
    with db_conn() as conn:
        conn.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?", (user["id"],))
        conn.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user["id"]),
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"] or user["username"].title(),
            "department": user["department"],
            "role": user["role"],
            "permissions": ROLE_PERMISSIONS.get(user["role"], ["query","chat"]),
        },
    }


@app.post("/api/v1/auth/logout")
async def logout(request: Request, token: str = Depends(oauth2_scheme)):
    p = verify_token(token)
    if p:
        blacklist_token(token)
        write_audit(p.get("user_id"), p.get("sub"), "logout")
    return {"message": "Logged out successfully"}


@app.get("/api/v1/auth/validate")
async def validate_token(p: dict = Depends(current_user)):
    return {"valid": True, "user": p["sub"], "role": p.get("role")}


@app.get("/api/v1/auth/me")
async def me(p: dict = Depends(current_user)):
    return {
        "id": p.get("user_id"),
        "username": p.get("sub"),
        "email": p.get("email"),
        "full_name": p.get("full_name"),
        "department": p.get("dept_id"),
        "role": p.get("role"),
        "permissions": p.get("permissions", []),
        "clearance_level": p.get("clearance_level"),
    }


@app.post("/api/v1/auth/mfa/verify")
async def mfa_verify(body: dict):
    code = body.get("code", "")
    if len(code) == 6 and code.isdigit():
        pending = body.get("pending_token") or body.get("session_token")
        if pending:
            p = verify_token(pending)
            if p:
                return {"status": "success", "access_token": pending,
                        "token_type": "bearer", "message": "MFA verified"}
        return {"status": "success", "access_token": "dev-bypass-token",
                "token_type": "bearer", "message": "MFA verified (dev mode)"}
    raise HTTPException(status_code=400, detail="Invalid MFA code — must be 6 digits")


@app.post("/api/v1/auth/mfa/setup")
async def mfa_setup(p: dict = Depends(current_user)):
    return {"status": "success", "secret": "DEMO_SECRET_KEY",
            "qr_code": f"otpauth://totp/Huron:{p.get('sub')}?secret=DEMO_SECRET_KEY&issuer=Huron",
            "message": "MFA setup initialized"}


# ═════════════════════════════════════════════════════════════════════════════
# ROOT-ONLY
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/root/users")
async def root_list_users(p: dict = Depends(require_root)):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT u.id,u.username,u.email,u.full_name,u.role,u.department,"
            "u.is_active,u.last_login,u.created_at,c.username as created_by_name "
            "FROM users u LEFT JOIN users c ON u.created_by=c.id ORDER BY u.created_at DESC"
        ).fetchall()
    return {"users": [dict(r) for r in rows]}


@app.post("/api/v1/root/users")
async def root_create_user(body: CreateUserRequest, p: dict = Depends(require_root)):
    if body.role == "root":
        raise HTTPException(status_code=400, detail="Cannot create another root user")
    ph = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    try:
        with db_conn() as conn:
            conn.execute(
                "INSERT INTO users (username,email,full_name,password_hash,role,department,created_by) "
                "VALUES (?,?,?,?,?,?,?)",
                (body.username, body.email, body.full_name, ph, body.role, body.department, p["user_id"]),
            )
            conn.execute("UPDATE departments SET user_count=user_count+1 WHERE code=?", (body.department,))
            conn.commit()
    except Exception as e:
        if isinstance(e, sqlite3.IntegrityError) or "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Username or email already exists")
        raise
    write_audit(p["user_id"], p["sub"], "create_user", body.department,
                detail=f"Created {body.role} {body.username}")
    return {"status": "success", "message": f"User {body.username} created"}


# FIX 1: Frontend uses PATCH — add PATCH alias alongside PUT
@app.put("/api/v1/root/users/{user_id}")
@app.patch("/api/v1/root/users/{user_id}")
async def root_update_user(user_id: int, body: UpdateUserRequest, p: dict = Depends(require_root)):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "root":
        raise HTTPException(status_code=400, detail="Cannot modify root user")

    updates, vals = [], []
    if body.full_name  is not None: updates.append("full_name=?");  vals.append(body.full_name)
    if body.role       is not None: updates.append("role=?");       vals.append(body.role)
    if body.department is not None: updates.append("department=?"); vals.append(body.department)
    if body.is_active  is not None: updates.append("is_active=?");  vals.append(bool(body.is_active))

    if updates:
        vals.append(user_id)
        with db_conn() as conn:
            conn.execute(
                f"UPDATE users SET {','.join(updates)},updated_at=CURRENT_TIMESTAMP WHERE id=?", vals
            )
            conn.commit()
    write_audit(p["user_id"], p["sub"], "update_user", detail=f"Updated {target['username']}")
    return {"status": "success"}


@app.delete("/api/v1/root/users/{user_id}")
async def root_delete_user(user_id: int, p: dict = Depends(require_root)):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "root":
        raise HTTPException(status_code=400, detail="Cannot delete root user")
    with db_conn() as conn:
        conn.execute("UPDATE users SET is_active=? WHERE id=?", (False, user_id))
        conn.execute(
            "UPDATE departments SET user_count=GREATEST(0,user_count-1) WHERE code=?",
            (target["department"],),
        )
        conn.commit()
    write_audit(p["user_id"], p["sub"], "deactivate_user", detail=f"Deactivated {target['username']}")
    return {"status": "success"}


@app.get("/api/v1/root/departments")
async def root_list_departments(p: dict = Depends(require_root)):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT d.*,u.username as admin_username FROM departments d "
            "LEFT JOIN users u ON d.admin_user_id=u.id"
        ).fetchall()
    return {"departments": [dict(r) for r in rows]}


@app.post("/api/v1/root/departments/{code}/assign-admin")
async def assign_dept_admin(code: str, body: dict, p: dict = Depends(require_root)):
    user = get_user_by_id(body.get("user_id"))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    with db_conn() as conn:
        conn.execute("UPDATE departments SET admin_user_id=? WHERE code=?", (user["id"], code))
        conn.execute("UPDATE users SET role='dept_admin',department=? WHERE id=?", (code, user["id"]))
        conn.commit()
    write_audit(p["user_id"], p["sub"], "assign_dept_admin", code,
                detail=f"Assigned {user['username']} as admin of {code}")
    return {"status": "success"}


@app.get("/api/v1/root/audit-log")
async def get_audit_log(
    limit: int = 100, dept: Optional[str] = None,
    action: Optional[str] = None, p: dict = Depends(require_root),
):
    q    = "SELECT * FROM audit_log WHERE 1=1"
    args: list = []
    if dept:   q += " AND dept_code=?";  args.append(dept)
    if action: q += " AND action=?";     args.append(action)
    q += " ORDER BY created_at DESC LIMIT ?"; args.append(limit)
    with db_conn() as conn:
        rows = conn.execute(q, args).fetchall()
    return {"audit_log": [dict(r) for r in rows]}


# ═════════════════════════════════════════════════════════════════════════════
# DEPT ADMIN  (canonical paths + FIX 2: /dept-admin/users aliases)
# ═════════════════════════════════════════════════════════════════════════════

async def _list_dept_users(p: dict) -> dict:
    with db_conn() as conn:
        if p["role"] == "root":
            rows = conn.execute(
                "SELECT id,username,email,full_name,role,department,is_active,last_login "
                "FROM users ORDER BY department,role"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,username,email,full_name,role,department,is_active,last_login "
                "FROM users WHERE department=? ORDER BY role",
                (p["dept_id"],),
            ).fetchall()
    return {"users": [dict(r) for r in rows]}


async def _create_dept_user(body: CreateUserRequest, p: dict) -> dict:
    adept = p.get("dept_id")
    if p["role"] != "root" and body.department != adept:
        raise HTTPException(status_code=403, detail=f"Can only create users in {adept}")
    if body.role in ("root", "dept_admin") and p["role"] != "root":
        raise HTTPException(status_code=403, detail="Only root can create admin-level users")
    ph = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    try:
        with db_conn() as conn:
            conn.execute(
                "INSERT INTO users (username,email,full_name,password_hash,role,department,created_by) "
                "VALUES (?,?,?,?,?,?,?)",
                (body.username, body.email, body.full_name, ph, body.role, body.department, p["user_id"]),
            )
            conn.execute("UPDATE departments SET user_count=user_count+1 WHERE code=?", (body.department,))
            conn.commit()
    except Exception as e:
        if isinstance(e, sqlite3.IntegrityError) or "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Username or email already exists")
        raise
    write_audit(p["user_id"], p["sub"], "create_user", body.department,
                detail=f"Created {body.role} {body.username}")
    return {"status": "success", "message": f"User {body.username} created"}


# Canonical paths
@app.get("/api/v1/admin/dept-users")
async def admin_list_dept_users(p: dict = Depends(require_admin)):
    return await _list_dept_users(p)


@app.post("/api/v1/admin/dept-users")
async def admin_create_dept_user(body: CreateUserRequest, p: dict = Depends(require_admin)):
    return await _create_dept_user(body, p)


# FIX 2: aliases — frontend calls /api/v1/dept-admin/users
@app.get("/api/v1/dept-admin/users")
async def dept_admin_list_users_alias(p: dict = Depends(require_admin)):
    return await _list_dept_users(p)


@app.post("/api/v1/dept-admin/users")
async def dept_admin_create_user_alias(body: CreateUserRequest, p: dict = Depends(require_admin)):
    return await _create_dept_user(body, p)


@app.put("/api/v1/admin/dept-users/{user_id}")
@app.patch("/api/v1/admin/dept-users/{user_id}")
async def admin_update_dept_user(
    user_id: int, body: UpdateUserRequest, p: dict = Depends(require_admin)
):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if p["role"] != "root" and target["department"] != p["dept_id"]:
        raise HTTPException(status_code=403, detail="Cannot modify users outside your department")
    if target["role"] == "root":
        raise HTTPException(status_code=403, detail="Cannot modify root user")

    updates, vals = [], []
    if body.full_name is not None: updates.append("full_name=?"); vals.append(body.full_name)
    if body.role is not None and p["role"] == "root":
        updates.append("role=?"); vals.append(body.role)
    if body.is_active is not None:
        updates.append("is_active=?"); vals.append(bool(body.is_active))

    if updates:
        vals.append(user_id)
        with db_conn() as conn:
            conn.execute(
                f"UPDATE users SET {','.join(updates)},updated_at=CURRENT_TIMESTAMP WHERE id=?", vals
            )
            conn.commit()
    write_audit(p["user_id"], p["sub"], "update_user",
                target["department"], detail=f"Updated {target['username']}")
    return {"status": "success"}


# Compat alias
@app.get("/api/v1/admin/users")
async def list_users_compat(p: dict = Depends(require_admin)):
    return await _list_dept_users(p)


# ═════════════════════════════════════════════════════════════════════════════
# ACCESS REQUESTS
# ═════════════════════════════════════════════════════════════════════════════

REQUESTABLE_TABS = [
    "query","chat","ingest","research","agent",
    "analytics","mcp","admin","cross_dept_query",
]

TAB_DESC = {
    "query":            "Search your department's knowledge base",
    "chat":             "Conversational AI with department documents",
    "ingest":           "Upload and index new documents",
    "research":         "Deep multi-source research mode",
    "agent":            "Autonomous AI agent with multi-step reasoning",
    "analytics":        "Usage analytics and query statistics",
    "mcp":              "Model Context Protocol tool integrations",
    "admin":            "Administrative panel access",
    "cross_dept_query": "Query documents across multiple departments",
}


@app.get("/api/v1/access-requests/tabs")
async def list_requestable_tabs(p: dict = Depends(current_user)):
    perms = set(p.get("permissions", []))
    return {
        "tabs": [
            {
                "tab": t,
                "label": t.replace("_", " ").title(),
                "description": TAB_DESC.get(t, t),
                "currently_accessible": t in perms,
                "requires_approval_from": "dept_admin" if t != "admin" else "root",
            }
            for t in REQUESTABLE_TABS
        ],
        "user_role": p.get("role"),
    }


@app.post("/api/v1/access-requests")
async def submit_access_request(body: AccessRequestCreate, p: dict = Depends(current_user)):
    if body.requested_tab not in REQUESTABLE_TABS:
        raise HTTPException(status_code=400, detail=f"Invalid tab: {body.requested_tab}")
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO access_requests "
            "(requester_id,dept_code,requested_tab,requested_role,justification) VALUES (?,?,?,?,?)",
            (p["user_id"], body.dept_code, body.requested_tab, body.requested_role, body.justification),
        )
        conn.commit()
    return {"status": "success", "message": "Request submitted for review"}


# FIX 3: Accept both ?status= and ?status_filter= (frontend uses ?status=)
@app.get("/api/v1/access-requests")
async def list_access_requests(
    status: Optional[str] = None,        # frontend sends ?status=
    status_filter: Optional[str] = None, # compat
    p: dict = Depends(current_user),
):
    filter_val = status or status_filter
    role = p["role"]
    q = """
        SELECT ar.*, u.username as requester_name, u.email as requester_email,
               r.username as reviewer_name
        FROM access_requests ar
        JOIN users u ON ar.requester_id=u.id
        LEFT JOIN users r ON ar.reviewed_by=r.id
        WHERE 1=1
    """
    args: list = []
    if role == "root":
        pass
    elif role == "dept_admin":
        q += " AND ar.dept_code=?"; args.append(p["dept_id"])
    else:
        q += " AND ar.requester_id=?"; args.append(p["user_id"])

    if filter_val:
        q += " AND ar.status=?"; args.append(filter_val)

    q += " ORDER BY ar.created_at DESC"
    with db_conn() as conn:
        rows = conn.execute(q, args).fetchall()
    return {"requests": [dict(r) for r in rows]}


@app.post("/api/v1/access-requests/review")
async def review_access_request(body: AccessRequestReview, p: dict = Depends(require_admin)):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM access_requests WHERE id=?", (body.request_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
        req = dict(row)
        if p["role"] == "dept_admin" and req["dept_code"] != p["dept_id"]:
            raise HTTPException(status_code=403, detail="Not your department's request")

        new_status = "approved" if body.action == "approve" else "rejected"
        conn.execute(
            "UPDATE access_requests SET status=?,reviewed_by=?,reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_status, p["user_id"], body.request_id),
        )
        if body.action == "approve":
            conn.execute(
                "UPDATE users SET role=? WHERE id=? AND role NOT IN ('root','dept_admin')",
                (req["requested_role"], req["requester_id"]),
            )
        conn.commit()

    write_audit(p["user_id"], p["sub"], f"{body.action}_request",
                detail=f"Request ID {body.request_id}")
    return {"status": "success", "new_status": new_status}


# ═════════════════════════════════════════════════════════════════════════════
# FEEDBACK (thumbs up / down — used to retrain / evaluate the model)
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/feedback")
async def submit_feedback(body: FeedbackRequest, p: dict = Depends(current_user)):
    if body.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="rating must be 1 (up) or -1 (down)")
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO feedback_log "
            "(user_id,username,dept_code,query_text,response,source,rating,comment) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (p.get("user_id"), p.get("sub"), body.dept_code,
             body.query[:500], body.response[:1000],
             body.source, body.rating, body.comment),
        )
        conn.commit()
    write_audit(p.get("user_id"), p.get("sub"), "feedback", body.dept_code,
                detail=f"rating={'👍' if body.rating == 1 else '👎'} source={body.source}")
    return {"status": "success"}


@app.get("/api/v1/feedback")
async def list_feedback(
    limit: int = 100,
    dept: Optional[str] = None,
    rating: Optional[int] = None,
    p: dict = Depends(require_admin),
):
    q    = "SELECT * FROM feedback_log WHERE 1=1"
    args: list = []
    if p["role"] == "dept_admin":
        q += " AND dept_code=?"; args.append(p["dept_id"])
    elif dept:
        q += " AND dept_code=?"; args.append(dept)
    if rating is not None:
        q += " AND rating=?"; args.append(rating)
    q += " ORDER BY created_at DESC LIMIT ?"; args.append(limit)
    with db_conn() as conn:
        rows = conn.execute(q, args).fetchall()
    return {"feedback": [dict(r) for r in rows], "total": len(rows)}


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS  [FIX 4]
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/admin/stats")
async def get_stats(p: dict = Depends(current_user)):
    role = p["role"]
    dept = p["dept_id"]

    with db_conn() as conn:
        users_q  = "SELECT COUNT(*) AS n FROM users WHERE is_active=1" + ("" if role == "root" else " AND department=?")
        today    = datetime.utcnow().date().isoformat()
        qlog_q   = "SELECT COUNT(*) AS n FROM query_log WHERE created_at>=?" + ("" if role == "root" else " AND dept_code=?")
        avgrt_q  = (
            "SELECT AVG(response_ms) AS v FROM (SELECT response_ms FROM query_log ORDER BY id DESC LIMIT 100) AS _sub"
            if role == "root" else
            "SELECT AVG(response_ms) AS v FROM (SELECT response_ms FROM query_log WHERE dept_code=? ORDER BY id DESC LIMIT 100) AS _sub"
        )
        faith_q  = (
            "SELECT AVG(faithfulness) AS v FROM query_log WHERE faithfulness IS NOT NULL"
            if role == "root" else
            "SELECT AVG(faithfulness) AS v FROM query_log WHERE dept_code=? AND faithfulness IS NOT NULL"
        )
        # Use COALESCE subquery so fetchone() always returns exactly one row
        docs_q = (
            "SELECT COALESCE(SUM(doc_count), 0) AS n FROM departments"
            if role == "root" else
            "SELECT COALESCE((SELECT doc_count FROM departments WHERE code=?), 0) AS n"
        )
        depts_q  = "SELECT COUNT(*) AS n FROM departments WHERE is_active=1"

        def _val(q, params, key):
            row = conn.execute(q, params).fetchone()
            return row[key] if row else None

        total_users   = _val(users_q,  () if role == "root" else (dept,), "n")
        queries_today = _val(qlog_q,   (today,) if role == "root" else (today, dept), "n")
        avg_rt        = _val(avgrt_q,  () if role == "root" else (dept,), "v")
        avg_faith     = _val(faith_q,  () if role == "root" else (dept,), "v")
        total_docs    = _val(docs_q,   () if role == "root" else (dept,), "n")
        dept_count    = _val(depts_q,  (), "n")

    pinecone_info: dict = {}
    try:
        from pinecone import Pinecone as PC
        idx = os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge")
        PC(api_key=os.getenv("PINECONE_API_KEY", "")).describe_index(idx)
        pinecone_info = {"status": "connected", "index": idx}
    except Exception as e:
        pinecone_info = {"status": "unavailable", "error": str(e)}

    return {
        "total_documents":   int(total_docs    or 0),
        "queries_today":     int(queries_today or 0),
        "active_users":      int(total_users   or 0),
        "total_users":       int(total_users   or 0),
        "departments":       int(dept_count    or 0),
        "avg_response_time": round((avg_rt    or 0) / 1000, 2),
        "avg_faithfulness":  round((avg_faith or 0), 2),
        "pinecone":          pinecone_info,
        "scope":             "global" if role == "root" else dept,
    }


@app.get("/api/v1/admin/stats/recent-queries")
async def recent_queries(limit: int = 20, p: dict = Depends(current_user)):
    role = p["role"]
    dept = p["dept_id"]
    with db_conn() as conn:
        if role == "root":
            rows = conn.execute(
                "SELECT ql.id, ql.dept_code as department, ql.query_text, "
                "ql.response_ms, ql.created_at as timestamp, u.username "
                "FROM query_log ql LEFT JOIN users u ON ql.user_id=u.id "
                "ORDER BY ql.created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ql.id, ql.dept_code as department, ql.query_text, "
                "ql.response_ms, ql.created_at as timestamp, u.username "
                "FROM query_log ql LEFT JOIN users u ON ql.user_id=u.id "
                "WHERE ql.dept_code=? ORDER BY ql.created_at DESC LIMIT ?",
                (dept, limit),
            ).fetchall()
    return {"queries": [dict(r) for r in rows]}


@app.get("/api/v1/admin/departments")
async def list_departments(p: dict = Depends(current_user)):
    role = p["role"]
    dept = p["dept_id"]
    with db_conn() as conn:
        if role == "root":
            rows = conn.execute(
                "SELECT d.*,u.username as admin_username,u.email as admin_email "
                "FROM departments d LEFT JOIN users u ON d.admin_user_id=u.id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT d.*,u.username as admin_username FROM departments d "
                "LEFT JOIN users u ON d.admin_user_id=u.id WHERE d.code=?", (dept,)
            ).fetchall()
    return {"departments": [dict(r) for r in rows]}


# ═════════════════════════════════════════════════════════════════════════════
# SOURCE GUARD — detect RAG hallucinations before returning to the user
# ═════════════════════════════════════════════════════════════════════════════

SOURCE_GUARD_ENABLED   = os.getenv("SOURCE_GUARD_ENABLED", "true").lower() == "true"
SOURCE_GUARD_THRESHOLD = float(os.getenv("SOURCE_GUARD_THRESHOLD", "0.6"))


async def _source_guard(query: str, response: str,
                        sources: list, faithfulness_score: Optional[float]) -> dict:
    """
    Two-layer hallucination check:
      1. Use faithfulness_score from the RAG orchestrator if available.
      2. Fall back to a fast LLM sanity-check using gpt-4o-mini (<100 tokens).
    Returns {"passed": bool, "score": float, "warning": str|None}
    """
    if not SOURCE_GUARD_ENABLED or not sources:
        return {"passed": True, "score": 1.0, "warning": None}

    # Layer 1: trust the RAG pipeline's own score
    if faithfulness_score is not None:
        passed  = faithfulness_score >= SOURCE_GUARD_THRESHOLD
        warning = None if passed else "RAG faithfulness score is low — verify against source documents."
        return {"passed": passed, "score": faithfulness_score, "warning": warning}

    # Layer 2: lightweight LLM check (only when no faithfulness score)
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"passed": True, "score": 1.0, "warning": None}

    titles = ", ".join(s.get("title", "") for s in sources if s.get("title"))
    prompt = (
        f"You are a hallucination detector.\n"
        f"Query: {query[:300]}\n"
        f"Response: {response[:500]}\n"
        f"Source documents: {titles}\n\n"
        f"Does the response appear grounded in these sources? "
        f'Reply with JSON only: {{"score": 0-10, "warning": "brief concern or null"}}'
    )

    try:
        from openai import AsyncOpenAI
        import json as _json
        client = AsyncOpenAI(api_key=api_key)
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0,
        )
        raw = _json.loads(r.choices[0].message.content or "{}")
        score   = float(raw.get("score", 10)) / 10.0
        warning = raw.get("warning") if score < SOURCE_GUARD_THRESHOLD else None
        return {"passed": score >= SOURCE_GUARD_THRESHOLD, "score": round(score, 2), "warning": warning}
    except Exception as exc:
        logger.debug("Source guard LLM check skipped: %s", exc)
        return {"passed": True, "score": 1.0, "warning": None}


# ═════════════════════════════════════════════════════════════════════════════
# LLM DIRECT FALLBACK — used when RAG pipeline / documents are unavailable
# ═════════════════════════════════════════════════════════════════════════════

DEPT_LABELS = {
    "hr": "Human Resources", "legal": "Legal", "finance": "Finance",
    "clinical": "Clinical", "operations": "Operations",
    "it": "IT & Engineering", "marketing": "Marketing",
    "external": "External Sources", "all": "All Departments",
}


_DEPTH_TOKENS = {3: 350, 5: 600, 10: 900, 15: 1300, 20: 1600}


async def _llm_direct(messages: list[dict], dept: str, top_k: int = 5) -> dict:
    """Call OpenAI directly — fallback when RAG pipeline or documents are unavailable."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {
            "status": "error",
            "response": (
                "The knowledge base is not available and no AI API key is configured. "
                "Please ask your administrator to set OPENAI_API_KEY."
            ),
            "source": "error",
            "sources": [],
        }

    dept_label = DEPT_LABELS.get(dept, dept.replace("_", " ").title()) if dept else "General"
    system_msg = (
        f"You are Huron, an AI knowledge assistant for the {dept_label} department at Huron VaultMind. "
        "You are currently responding from your general knowledge because no department documents "
        "have been indexed yet, or the knowledge base is temporarily unavailable. "
        "Be helpful, professional, and concise. "
        "At the end of every response, add a brief note reminding the user that this answer is "
        "based on general AI knowledge and not on company-specific documents."
    )

    conv = [{"role": "system", "content": system_msg}] + [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("role") in ("user", "assistant")
    ]

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            messages=conv,
            max_tokens=_DEPTH_TOKENS.get(top_k, 600),
            temperature=0.7,
        )
        answer = resp.choices[0].message.content or ""
        return {
            "status": "success",
            "response": answer,
            "source": "general_knowledge",
            "source_label": f"General knowledge — no {dept_label} documents indexed",
            "sources": [],
        }
    except Exception as exc:
        logger.warning("LLM direct fallback error: %s", exc)
        return {
            "status": "error",
            "response": (
                "I'm unable to respond right now. The knowledge base is unavailable and "
                "the AI service returned an error. Please try again later."
            ),
            "source": "error",
            "sources": [],
        }


# ═════════════════════════════════════════════════════════════════════════════
# QUERY / CHAT / INGEST
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/query")
async def query_endpoint(req: QueryRequest, p: dict = Depends(current_user)):
    perm(p, "query")
    dept = req.department or p.get("dept_id", "general")
    dept_gate(p, dept)

    rag = get_rag()
    if not rag:
        fb = await _llm_direct([{"role": "user", "content": req.query}], dept, req.top_k)
        log_query(p.get("user_id", 0), dept, req.query, 0, 0, 0)
        return {
            "status":  fb["status"],
            "query":   req.query,
            "results": fb["response"],
            "sources": [],
            "source":  fb.get("source", "general_knowledge"),
            "source_label": fb.get("source_label", ""),
        }

    # ── Cache check ───────────────────────────────────────────────────────────
    cached = _cache_get(dept, req.query)
    if cached:
        logger.debug("Query cache hit: dept=%s", dept)
        return {**cached, "cache_hit": True}

    t0 = time.time()
    try:
        from utils.tenant_context import TenantContext
        ctx    = TenantContext(tenant_id="huron", dept_id=dept,
                               username=p.get("sub"), role=p.get("role", "user"))
        result  = await rag.query(query=req.query, tenant_context=ctx)
        elapsed = int((time.time() - t0) * 1000)
        sources = [{"title": s} for s in result.get("sources", [])]
        faith   = result.get("faithfulness_score")
        log_query(p.get("user_id", 0), dept, req.query, elapsed, faith or 0, len(sources))
        guard   = await _source_guard(req.query, result.get("response", ""), sources, faith)
        payload = {
            "status":             "success",
            "query":              req.query,
            "results":            result.get("response", ""),
            "sources":            sources,
            "source":             "rag",
            "source_guard":       guard,
            "intent":             result.get("intent"),
            "faithfulness_score": faith,
            "processing_time_ms": elapsed,
        }
        _cache_set(dept, req.query, payload)
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat")
async def chat_endpoint(req: ChatRequest, p: dict = Depends(current_user)):
    perm(p, "chat")
    dept = req.department or p.get("dept_id", "general")
    dept_gate(p, dept)
    last = next((m["content"] for m in reversed(req.messages) if m.get("role") == "user"), "")

    rag = get_rag()
    if not rag:
        return await _llm_direct(req.messages, dept)

    try:
        from utils.tenant_context import TenantContext
        ctx    = TenantContext(tenant_id="huron", dept_id=dept,
                               username=p.get("sub"), role=p.get("role", "user"))
        result  = await rag.query(query=last, tenant_context=ctx)
        sources = [{"title": s} for s in result.get("sources", [])]
        faith   = result.get("faithfulness_score")
        guard   = await _source_guard(last, result.get("response", ""), sources, faith)
        return {
            "status":             "success",
            "response":           result.get("response", ""),
            "source":             "rag",
            "sources":            sources,
            "source_guard":       guard,
            "faithfulness_score": faith,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/research")
async def research_endpoint(req: ResearchRequest, p: dict = Depends(current_user)):
    perm(p, "research")
    dept = req.dept or p.get("dept_id", "general")
    dept_gate(p, dept)

    internal_results: list[dict] = []
    web_results:      list[dict] = []
    synthesis = ""

    # ── 1. Internal docs via RAG ──────────────────────────────────────────────
    if req.use_internal:
        rag = get_rag()
        if rag:
            try:
                from utils.tenant_context import TenantContext
                ctx = TenantContext(tenant_id="huron", dept_id=dept,
                                    username=p.get("sub"), role=p.get("role", "user"))
                res = await rag.query(query=req.query, tenant_context=ctx)
                if res.get("response"):
                    internal_results.append({
                        "title": "Internal Knowledge Summary",
                        "snippet": res["response"],
                        "is_summary": True,
                        "dept": dept,
                    })
                for s in res.get("sources", []):
                    internal_results.append({"title": s, "snippet": "", "dept": dept})
            except Exception as exc:
                logger.warning("Research RAG error: %s", exc)

    # ── 2. Cross-dept search ───────────────────────────────────────────────────
    if req.use_cross_dept and p.get("role") in ("root", "power_user"):
        rag = get_rag()
        if rag:
            cross = [d for d in
                     ["hr", "finance", "legal", "clinical", "operations", "it", "marketing"]
                     if d != dept]
            for xd in cross:
                try:
                    from utils.tenant_context import TenantContext
                    ctx = TenantContext(tenant_id="huron", dept_id=xd,
                                        username=p.get("sub"), role=p.get("role", "user"))
                    res = await rag.query(query=req.query, tenant_context=ctx)
                    for s in res.get("sources", []):
                        internal_results.append({"title": s, "snippet": "", "dept": xd})
                except Exception as exc:
                    logger.debug("Cross-dept %s error: %s", xd, exc)

    # ── 3. Web search ─────────────────────────────────────────────────────────
    if req.use_web:
        # Try DuckDuckGo first; fall back to Wikipedia if it returns nothing.
        def _ddgs_search() -> list[dict]:
            try:
                from duckduckgo_search import DDGS
                with DDGS(timeout=10) as ddgs:
                    raw = list(ddgs.text(req.query, max_results=6))
                return [
                    {"title": r.get("title",""), "url": r.get("href",""), "snippet": r.get("body","")}
                    for r in raw
                ]
            except Exception as exc:
                logger.debug("DDGS search unavailable: %s", exc)
                return []

        def _wiki_search() -> list[dict]:
            import urllib.request as _req
            import urllib.parse as _parse
            import json as _json
            params = _parse.urlencode({
                "action": "query", "list": "search",
                "srsearch": req.query, "srlimit": 6,
                "format": "json", "srprop": "snippet",
            })
            url = f"https://en.wikipedia.org/w/api.php?{params}"
            request = _req.Request(url, headers={"User-Agent": "HuronResearch/1.0"})
            with _req.urlopen(request, timeout=10) as resp:
                data = _json.loads(resp.read())
            results = []
            for item in data.get("query", {}).get("search", []):
                title   = item.get("title", "")
                snippet = item.get("snippet", "")
                # strip Wikipedia highlight markup
                for tag in ('<span class="searchmatch">', '</span>'):
                    snippet = snippet.replace(tag, "")
                import urllib.parse as _p
                results.append({
                    "title":   title,
                    "url":     f"https://en.wikipedia.org/wiki/{_p.quote(title.replace(' ','_'))}",
                    "snippet": snippet,
                })
            return results

        try:
            ddgs_results = await asyncio.to_thread(_ddgs_search)
            if ddgs_results:
                web_results = ddgs_results
                logger.debug("Web search: %d results via DuckDuckGo", len(web_results))
            else:
                web_results = await asyncio.to_thread(_wiki_search)
                logger.debug("Web search: %d results via Wikipedia fallback", len(web_results))
        except Exception as exc:
            logger.warning("Web search error: %s", exc)

    # ── 4. AI synthesis ───────────────────────────────────────────────────────
    if req.use_ai_analysis:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=api_key)
                parts: list[str] = []
                if internal_results:
                    lines = "\n".join(
                        f"- {r['title']}: {r.get('snippet', '')[:300]}"
                        for r in internal_results[:6]
                    )
                    parts.append(f"INTERNAL SOURCES:\n{lines}")
                if web_results:
                    lines = "\n".join(
                        f"- {r['title']}: {r.get('snippet', '')[:300]}"
                        for r in web_results[:5]
                    )
                    parts.append(f"WEB SOURCES:\n{lines}")
                context = "\n\n".join(parts) or "No source documents available."
                prompt = (
                    "You are a research analyst for Huron VaultMind.\n"
                    "Synthesize the following research into a professional briefing.\n\n"
                    f"RESEARCH QUERY: {req.query}\n\n"
                    f"{context}\n\n"
                    "Structure your response with:\n"
                    "**Key Findings** (bullet points)\n"
                    "**Summary** (2–3 paragraphs)\n"
                    "**Recommendations**\n\n"
                    "Cite whether insights come from internal documents or web sources."
                )
                resp = await client.chat.completions.create(
                    model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1200,
                    temperature=0.4,
                )
                synthesis = resp.choices[0].message.content or ""
            except Exception as exc:
                logger.warning("AI synthesis error: %s", exc)
                synthesis = "AI synthesis unavailable at this time."

    return {
        "status":           "success",
        "query":            req.query,
        "internal_results": internal_results,
        "web_results":      web_results,
        "synthesis":        synthesis,
    }


# ═════════════════════════════════════════════════════════════════════════════
# CONVERSATION MEMORY
# ═════════════════════════════════════════════════════════════════════════════

import uuid as _uuid


def _auto_title(first_message: str) -> str:
    """Generate a conversation title from the first user message."""
    words = first_message.strip().split()
    return " ".join(words[:8]) + ("…" if len(words) > 8 else "")


@app.post("/api/v1/conversations")
async def create_conversation(req: ConversationCreate, p: dict = Depends(current_user)):
    perm(p, "chat")
    conv_id = str(_uuid.uuid4())
    dept    = req.dept or p.get("dept_id", "general")
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (id, user_id, dept, tab, title) VALUES (?,?,?,?,?)",
            (conv_id, p["user_id"], dept, req.tab, req.title),
        )
        conn.commit()
    return {"id": conv_id, "title": req.title, "tab": req.tab, "dept": dept}


@app.get("/api/v1/conversations")
async def list_conversations(tab: Optional[str] = None, p: dict = Depends(current_user)):
    perm(p, "chat")
    with db_conn() as conn:
        if tab:
            rows = conn.execute(
                "SELECT id, title, tab, dept, created_at, updated_at "
                "FROM conversations WHERE user_id=? AND tab=? "
                "ORDER BY updated_at DESC LIMIT 50",
                (p["user_id"], tab),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, tab, dept, created_at, updated_at "
                "FROM conversations WHERE user_id=? "
                "ORDER BY updated_at DESC LIMIT 50",
                (p["user_id"],),
            ).fetchall()
    return {"conversations": [dict(r) for r in rows]}


@app.get("/api/v1/conversations/{conv_id}/messages")
async def get_conversation_messages(conv_id: str, p: dict = Depends(current_user)):
    perm(p, "chat")
    with db_conn() as conn:
        conv = conn.execute(
            "SELECT user_id FROM conversations WHERE id=?", (conv_id,)
        ).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["user_id"] != p["user_id"] and p.get("role") != "root":
            raise HTTPException(status_code=403, detail="Access denied")
        rows = conn.execute(
            "SELECT id, role, content, source, source_label, created_at "
            "FROM conversation_messages WHERE conversation_id=? "
            "ORDER BY created_at ASC",
            (conv_id,),
        ).fetchall()
    return {"conversation_id": conv_id, "messages": [dict(r) for r in rows]}


@app.post("/api/v1/conversations/{conv_id}/messages")
async def append_message(conv_id: str, req: MessageAppend, p: dict = Depends(current_user)):
    perm(p, "chat")
    with db_conn() as conn:
        conv = conn.execute(
            "SELECT user_id, title FROM conversations WHERE id=?", (conv_id,)
        ).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["user_id"] != p["user_id"] and p.get("role") != "root":
            raise HTTPException(status_code=403, detail="Access denied")
        conn.execute(
            "INSERT INTO conversation_messages "
            "(conversation_id, role, content, source, source_label) VALUES (?,?,?,?,?)",
            (conv_id, req.role, req.content, req.source, req.source_label),
        )
        # Auto-set title from first user message
        if req.role == "user" and conv["title"] in ("New Conversation", ""):
            conn.execute(
                "UPDATE conversations SET title=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (_auto_title(req.content), conv_id),
            )
        else:
            conn.execute(
                "UPDATE conversations SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (conv_id,),
            )
        conn.commit()
    return {"status": "ok"}


@app.delete("/api/v1/conversations/{conv_id}")
async def delete_conversation(conv_id: str, p: dict = Depends(current_user)):
    perm(p, "chat")
    with db_conn() as conn:
        conv = conn.execute(
            "SELECT user_id FROM conversations WHERE id=?", (conv_id,)
        ).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if conv["user_id"] != p["user_id"] and p.get("role") != "root":
            raise HTTPException(status_code=403, detail="Access denied")
        conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
        conn.commit()
    return {"status": "deleted"}


@app.post("/api/v1/ingest")
async def ingest_endpoint(
    file:              UploadFile = File(...),
    department:        str        = Form("general"),
    sensitivity_level: str        = Form("internal"),
    doc_id:            str        = Form(""),
    version:           str        = Form(""),
    token:             str        = Depends(oauth2_scheme),
):
    p = verify_token(token)
    if not p:
        raise HTTPException(status_code=401, detail="Invalid token")
    perm(p, "ingest")
    dept = department or p.get("dept_id", "general")
    dept_gate(p, dept)

    svc = get_svc()
    if not svc:
        return {"status": "degraded", "message": "Ingestion pipeline unavailable.",
                "file": file.filename, "department": dept, "namespace": "",
                "parent_chunks": 0, "child_chunks": 0, "pinecone_upsert": False, "warnings": []}

    try:
        content = await file.read()
        from utils.tenant_context import TenantContext
        ctx    = TenantContext(tenant_id="huron", dept_id=dept,
                               username=p.get("sub"), role=p.get("role", "user"))
        result = await svc.ingest_document(
            file_content=content, file_name=file.filename,
            tenant_context=ctx, sensitivity_level=sensitivity_level,
            doc_id=doc_id or None, version=version or None,
        )
        if result.success:
            with db_conn() as conn:
                conn.execute("UPDATE departments SET doc_count=doc_count+? WHERE code=?",
                             (result.parent_chunks, dept))
                conn.commit()
        write_audit(p.get("user_id"), p.get("sub"), "ingest",
                    dept, getattr(result, "namespace", ""), f"File: {file.filename}")
        return {
            "status":          "success" if result.success else "error",
            "document_id":     getattr(result, "document_id", ""),
            "version":         getattr(result, "version", ""),
            "file_type":       getattr(result, "file_type", ""),
            "file":            file.filename,
            "department":      dept,
            "namespace":       getattr(result, "namespace", ""),
            "parent_chunks":   getattr(result, "parent_chunks", 0),
            "child_chunks":    getattr(result, "child_chunks", 0),
            "pinecone_upsert": getattr(result, "_pinecone_upsert_success", False),
            "warnings":        getattr(result, "warnings", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═════════════════════════════════════════════════════════════════════════════
# DOCUMENT VERSION MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/documents/recent")
async def recent_document_versions(
    limit: int = 30,
    p: dict = Depends(current_user),
):
    """
    Return the most recent document version events.
    Root / dept_admin see all departments.
    Regular users see only their own department.
    Used by the Analytics version feed and header notifications.
    """
    role  = p.get("role", "user")
    udept = p.get("dept_id", "general")

    with db_conn() as conn:
        if role in ("root", "dept_admin", "power_user"):
            rows = conn.execute(
                """SELECT dv.dept, dv.doc_id, dv.version, dv.source_file,
                          dv.file_type, dv.chunk_count, dv.is_latest,
                          dv.ingested_by, dv.ingested_at,
                          d.display_name AS dept_name
                   FROM document_versions dv
                   LEFT JOIN departments d ON dv.dept = d.code
                   ORDER BY dv.ingested_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT dv.dept, dv.doc_id, dv.version, dv.source_file,
                          dv.file_type, dv.chunk_count, dv.is_latest,
                          dv.ingested_by, dv.ingested_at,
                          d.display_name AS dept_name
                   FROM document_versions dv
                   LEFT JOIN departments d ON dv.dept = d.code
                   WHERE dv.dept = ?
                   ORDER BY dv.ingested_at DESC LIMIT ?""",
                (udept, limit),
            ).fetchall()

    versions = []
    for r in rows:
        row = dict(r)
        # Normalise boolean for both SQLite (0/1) and PostgreSQL (bool)
        row["is_latest"] = bool(row.get("is_latest", 0))
        versions.append(row)

    return {"versions": versions}


@app.get("/api/v1/documents/{dept}")
async def list_documents(dept: str, token: str = Depends(oauth2_scheme)):
    """List all documents in a department with their latest version info."""
    p = verify_token(token)
    if not p:
        raise HTTPException(status_code=401, detail="Invalid token")
    dept_gate(p, dept)
    with db_conn() as conn:
        rows = conn.execute(
            """SELECT doc_id, version, source_file, file_type, effective_date,
                      chunk_count, ingested_by, ingested_at
               FROM document_versions
               WHERE dept=? AND is_latest=1
               ORDER BY ingested_at DESC""",
            (dept,),
        ).fetchall()
    return {"dept": dept, "documents": [
        {"doc_id": r[0], "version": r[1], "source_file": r[2], "file_type": r[3],
         "effective_date": r[4], "chunk_count": r[5], "ingested_by": r[6], "ingested_at": r[7]}
        for r in rows
    ]}


@app.get("/api/v1/documents/{dept}/{doc_id}/versions")
async def document_version_history(dept: str, doc_id: str, token: str = Depends(oauth2_scheme)):
    """Full version history for a document."""
    p = verify_token(token)
    if not p:
        raise HTTPException(status_code=401, detail="Invalid token")
    dept_gate(p, dept)
    with db_conn() as conn:
        rows = conn.execute(
            """SELECT version, source_file, file_type, effective_date,
                      chunk_count, is_latest, ingested_by, ingested_at
               FROM document_versions
               WHERE dept=? AND doc_id=?
               ORDER BY ingested_at DESC""",
            (dept, doc_id),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"dept": dept, "doc_id": doc_id, "versions": [
        {"version": r[0], "source_file": r[1], "file_type": r[2], "effective_date": r[3],
         "chunk_count": r[4], "is_latest": bool(r[5]), "ingested_by": r[6], "ingested_at": r[7]}
        for r in rows
    ]}


class RollbackRequest(BaseModel):
    version: str


@app.post("/api/v1/documents/{dept}/{doc_id}/rollback")
async def rollback_document(
    dept: str, doc_id: str, req: RollbackRequest, token: str = Depends(oauth2_scheme)
):
    """Roll back to a previous document version."""
    p = verify_token(token)
    if not p:
        raise HTTPException(status_code=401, detail="Invalid token")
    perm(p, "ingest")
    dept_gate(p, dept)

    with db_conn() as conn:
        target = conn.execute(
            "SELECT vector_ids FROM document_versions WHERE dept=? AND doc_id=? AND version=?",
            (dept, doc_id, req.version),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail=f"Version {req.version} not found")

        # Mark current latest as not-latest in DB
        conn.execute(
            "UPDATE document_versions SET is_latest=0 WHERE dept=? AND doc_id=? AND is_latest=1",
            (dept, doc_id),
        )
        # Mark target version as latest in DB
        conn.execute(
            "UPDATE document_versions SET is_latest=1 WHERE dept=? AND doc_id=? AND version=?",
            (dept, doc_id, req.version),
        )
        conn.commit()

    # Update Pinecone metadata
    namespace = f"vaultmind-huron-{dept}-general"
    try:
        from pinecone import Pinecone as PC
        idx = PC(api_key=os.getenv("PINECONE_API_KEY", "")).Index(
            os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge")
        )
        # Mark all versions for this doc as not-latest first
        with db_conn() as conn:
            all_rows = conn.execute(
                "SELECT version, vector_ids FROM document_versions WHERE dept=? AND doc_id=?",
                (dept, doc_id),
            ).fetchall()
        import json as _json
        for row_version, row_vids_json in all_rows:
            if not row_vids_json:
                continue
            vids       = _json.loads(row_vids_json)
            is_current = (row_version == req.version)
            for vid in vids:
                try:
                    idx.update(id=vid, set_metadata={"is_latest": is_current}, namespace=namespace)
                except Exception:
                    pass
    except Exception as e:
        logger.warning("Pinecone rollback metadata update failed: %s", e)

    write_audit(p.get("user_id"), p.get("sub"), "rollback", dept, namespace,
                f"doc_id={doc_id} rolled back to version={req.version}")
    return {"status": "success", "doc_id": doc_id, "active_version": req.version}


@app.delete("/api/v1/documents/{dept}/{doc_id}")
async def delete_document(dept: str, doc_id: str, token: str = Depends(oauth2_scheme)):
    """Delete all versions of a document from Pinecone and DB."""
    p = verify_token(token)
    if not p:
        raise HTTPException(status_code=401, detail="Invalid token")
    perm(p, "ingest")
    dept_gate(p, dept)

    namespace = f"vaultmind-huron-{dept}-general"
    deleted_chunks = 0

    with db_conn() as conn:
        rows = conn.execute(
            "SELECT vector_ids FROM document_versions WHERE dept=? AND doc_id=?",
            (dept, doc_id),
        ).fetchall()

    import json as _json
    all_vids: list = []
    for (vids_json,) in rows:
        if vids_json:
            all_vids.extend(_json.loads(vids_json))

    if all_vids:
        try:
            from pinecone import Pinecone as PC
            idx = PC(api_key=os.getenv("PINECONE_API_KEY", "")).Index(
                os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge")
            )
            for batch_start in range(0, len(all_vids), 100):
                idx.delete(ids=all_vids[batch_start:batch_start + 100], namespace=namespace)
            deleted_chunks = len(all_vids)
        except Exception as e:
            logger.warning("Pinecone delete failed: %s", e)

    with db_conn() as conn:
        conn.execute(
            "DELETE FROM document_versions WHERE dept=? AND doc_id=?", (dept, doc_id)
        )
        conn.commit()

    write_audit(p.get("user_id"), p.get("sub"), "delete_document", dept, namespace,
                f"doc_id={doc_id} deleted_chunks={deleted_chunks}")
    return {"status": "success", "doc_id": doc_id, "deleted_chunks": deleted_chunks}


# ═════════════════════════════════════════════════════════════════════════════
# HEALTH + INDEXES
# ═════════════════════════════════════════════════════════════════════════════

# ─── OIDC / SSO skeleton ─────────────────────────────────────────────────────
# Activated only when OIDC_CLIENT_ID is set.  All three vars must be present
# for SSO to function; missing any one will return 501 Not Implemented.
_OIDC_CLIENT_ID     = os.getenv("OIDC_CLIENT_ID", "")
_OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
_OIDC_AUTHORITY     = os.getenv("OIDC_AUTHORITY", "")   # e.g. https://login.microsoftonline.com/<tenant>
_OIDC_REDIRECT_URI  = os.getenv("OIDC_REDIRECT_URI", "http://localhost:3000/api/v1/auth/oidc/callback")

@app.get("/api/v1/auth/oidc/login")
async def oidc_login():
    """Redirect browser to Microsoft Entra ID (or any OIDC provider) login page."""
    if not (_OIDC_CLIENT_ID and _OIDC_AUTHORITY):
        raise HTTPException(status_code=501, detail="SSO not configured on this server")
    from urllib.parse import urlencode
    params = {
        "client_id":     _OIDC_CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  _OIDC_REDIRECT_URI,
        "scope":         "openid profile email",
        "state":         secrets.token_urlsafe(16),
    }
    auth_url = f"{_OIDC_AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=auth_url)


@app.get("/api/v1/auth/oidc/callback")
async def oidc_callback(code: str = "", error: str = "", state: str = ""):
    """Exchange OIDC auth code for tokens, map AD groups → Huron role, issue JWT."""
    if not (_OIDC_CLIENT_ID and _OIDC_CLIENT_SECRET and _OIDC_AUTHORITY):
        raise HTTPException(status_code=501, detail="SSO not configured on this server")
    if error:
        raise HTTPException(status_code=400, detail=f"OIDC provider error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    import httpx as _httpx
    token_url = f"{_OIDC_AUTHORITY}/oauth2/v2.0/token"
    resp = _httpx.post(token_url, data={
        "grant_type":    "authorization_code",
        "client_id":     _OIDC_CLIENT_ID,
        "client_secret": _OIDC_CLIENT_SECRET,
        "code":          code,
        "redirect_uri":  _OIDC_REDIRECT_URI,
    })
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to exchange OIDC code")

    id_token_claims = jwt.decode(resp.json()["id_token"], options={"verify_signature": False})
    email    = id_token_claims.get("preferred_username") or id_token_claims.get("email", "")
    ad_groups: list[str] = id_token_claims.get("groups", [])

    # Resolve Huron role from AD group mappings
    huron_role = "user"
    dept_code  = "general"
    with db_conn() as conn:
        for grp in ad_groups:
            row = conn.execute(
                "SELECT huron_role, dept_code FROM oidc_role_mappings WHERE ad_group=?", (grp,)
            ).fetchone()
            if row:
                huron_role = row["huron_role"]
                dept_code  = row["dept_code"] or "general"
                break

        # Auto-provision user on first SSO login
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if not existing:
            hashed = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username,email,password_hash,role,department,is_active,auth_method) "
                "VALUES (?,?,?,?,?,1,'oidc')",
                (email.split("@")[0], email, hashed, huron_role, dept_code),
            )
            conn.commit()
        user_row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    user_dict = dict(user_row)
    # create_token is defined below in the Auth section — forward call is fine
    token = create_token(user_dict)
    from fastapi.responses import RedirectResponse
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(url=f"{frontend_url}/auth/sso-complete?token={token}")


@app.get("/health")
async def health():
    checks: dict = {"version": "4.0.0", "timestamp": datetime.utcnow().isoformat()}

    # Database
    try:
        with db_conn() as conn:
            conn.execute("SELECT 1")
        checks["db"] = {"status": "ok", "backend": "postgresql" if DATABASE_URL else "sqlite"}
    except Exception as e:
        checks["db"] = {"status": "error", "detail": str(e)}

    # Redis (optional)
    if _redis_client:
        try:
            _redis_client.ping()
            checks["redis"] = {"status": "ok"}
        except Exception as e:
            checks["redis"] = {"status": "error", "detail": str(e)}
    else:
        checks["redis"] = {"status": "disabled"}

    # Pinecone (optional — only if API key present)
    _pinecone_key = os.getenv("PINECONE_API_KEY", "")
    if _pinecone_key:
        try:
            from pinecone import Pinecone as _PC
            _pc = _PC(api_key=_pinecone_key)
            _pc.list_indexes()
            checks["pinecone"] = {"status": "ok"}
        except Exception as e:
            checks["pinecone"] = {"status": "error", "detail": str(e)}
    else:
        checks["pinecone"] = {"status": "disabled"}

    overall = "healthy" if all(
        v.get("status") in ("ok", "disabled") for v in checks.values() if isinstance(v, dict)
    ) else "degraded"
    checks["status"] = overall
    return checks


@app.get("/api/v1/indexes")
async def list_indexes(p: dict = Depends(current_user)):
    role  = p.get("role", "user")
    udept = p.get("dept_id", "general")
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT code,display_name,namespace,doc_count,classification FROM departments WHERE is_active=1"
        ).fetchall()
    indexes = []
    for r in rows:
        # root / dept_admin / power_user see all; regular users see only their dept
        if role in ("root", "dept_admin", "power_user") or r["code"] == udept:
            indexes.append({
                "name": r["namespace"], "dept": r["code"],
                "display_name": r["display_name"],
                "type": "Pinecone", "documents": r["doc_count"],
                "classification": r["classification"], "status": "active",
            })
    return {"status": "success", "count": len(indexes), "indexes": indexes}


# ═════════════════════════════════════════════════════════════════════════════
# AGENT
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/agent/run")
async def agent_run(req: AgentRunRequest, p: dict = Depends(current_user)):
    perm(p, "agent")
    dept = req.dept or p.get("dept_id", "general")
    dept_gate(p, dept)

    import uuid
    run_id = str(uuid.uuid4())

    # Build TenantContext from JWT claims
    class _Ctx:
        def __init__(self, payload: dict):
            self.dept_id         = payload.get("dept_id", "general")
            self.namespace_scope = payload.get("namespace_scope", [self.dept_id])
            self.permissions     = payload.get("permissions", [])
            self.role            = payload.get("role", "user")

    ctx = _Ctx(p)

    # Persist run record
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO agent_runs (id,user_id,dept,query,status,model) VALUES (?,?,?,?,?,?)",
            (run_id, p.get("user_id"), dept, req.query, "running", req.model),
        )
        conn.commit()

    # Import here to avoid circular at module load
    from agent.react_agent import ReActAgent

    agent = ReActAgent(ctx, run_id, max_steps=req.max_steps, model=req.model)
    _active_runs[run_id] = agent
    _run_steps[run_id]   = []

    async def _run():
        try:
            async for step in agent.run(req.query):
                _run_steps[run_id].append(step)
            final = next(
                (s for s in reversed(_run_steps[run_id]) if s["type"] == "complete"), {}
            )
            with db_conn() as conn:
                import json as _json
                conn.execute(
                    "UPDATE agent_runs SET status=?,final_answer=?,steps=?,"
                    "namespaces_accessed=?,steps_taken=? WHERE id=?",
                    (
                        "complete",
                        final.get("answer", ""),
                        _json.dumps(_run_steps[run_id]),
                        _json.dumps(final.get("namespaces_accessed", [])),
                        final.get("steps_taken", 0),
                        run_id,
                    ),
                )
                conn.commit()
            write_audit(
                p.get("user_id"), p.get("sub"), "agent_run", dept,
                detail=f"run_id={run_id} steps={final.get('steps_taken', 0)}",
            )
        except Exception as e:
            _run_steps[run_id].append({"type": "error", "message": str(e)})
            with db_conn() as conn:
                conn.execute("UPDATE agent_runs SET status=? WHERE id=?", ("error", run_id))
                conn.commit()

    asyncio.create_task(_run())
    return {"run_id": run_id, "status": "running", "dept": dept}


@app.get("/api/v1/agent/stream/{run_id}")
async def agent_stream(run_id: str, request: Request, token: Optional[str] = None):
    """
    SSE endpoint — streams agent steps as they are produced.
    Auth: reads token from query param (?token=...) because EventSource
    does not support custom headers.
    """
    import json as _json

    # Resolve token from query param (SSE) or Authorization header
    raw_token = token
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header[7:]

    p = verify_token(raw_token or "")
    if not p:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify run belongs to requesting user (or root)
    with db_conn() as conn:
        row = conn.execute(
            "SELECT user_id, status FROM agent_runs WHERE id=?", (run_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    if row["user_id"] != p.get("user_id") and p.get("role") != "root":
        raise HTTPException(status_code=403, detail="Not your run")

    async def event_stream():
        sent      = 0
        polls     = 0
        max_polls = 600   # 5-min timeout at 0.5s intervals
        while polls < max_polls:
            steps = _run_steps.get(run_id, [])
            while sent < len(steps):
                step = steps[sent]
                yield f"event: step\ndata: {_json.dumps(step)}\n\n"
                sent += 1
                if step["type"] in ("complete", "error"):
                    return
            await asyncio.sleep(0.5)
            polls += 1
        yield f'event: timeout\ndata: {{"message":"Stream timeout"}}\n\n'

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/v1/agent/stop/{run_id}")
async def agent_stop(run_id: str, p: dict = Depends(current_user)):
    agent = _active_runs.get(run_id)
    if agent:
        agent.stop()
        with db_conn() as conn:
            conn.execute("UPDATE agent_runs SET status=? WHERE id=?", ("stopped", run_id))
            conn.commit()
    return {"status": "stopped", "run_id": run_id}


@app.get("/api/v1/agent/runs")
async def list_agent_runs(limit: int = 20, p: dict = Depends(current_user)):
    with db_conn() as conn:
        if p.get("role") == "root":
            rows = conn.execute(
                "SELECT id,user_id,dept,query,status,steps_taken,model,created_at "
                "FROM agent_runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,user_id,dept,query,status,steps_taken,model,created_at "
                "FROM agent_runs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (p.get("user_id"), limit),
            ).fetchall()
    return {"runs": [dict(r) for r in rows]}


# ═════════════════════════════════════════════════════════════════════════════
# MCP — Model Context Protocol action layer
# ═════════════════════════════════════════════════════════════════════════════

class McpToolCreate(BaseModel):
    name:        str
    category:    str = "communication"
    description: str = ""
    tool_type:   str
    dept_scope:  Optional[str] = None
    min_role:    str = "user"
    is_enabled:  bool = True

class McpToolUpdate(BaseModel):
    name:        Optional[str]  = None
    description: Optional[str]  = None
    dept_scope:  Optional[str]  = None
    min_role:    Optional[str]  = None
    is_enabled:  Optional[bool] = None

class McpConfigSet(BaseModel):
    dept_code: str
    config:    dict

class McpRunRequest(BaseModel):
    tool_id:     int
    result_text: str
    query:       str
    user_params: dict = {}


def _can_run_tool(user_role: str, min_role: str, user_dept: str, dept_scope: Optional[str]) -> bool:
    clearance = {"root": 5, "dept_admin": 4, "power_user": 3, "user": 2, "viewer": 1}
    if clearance.get(user_role, 0) < clearance.get(min_role, 2):
        return False
    if dept_scope and user_role != "root":
        if user_dept not in [d.strip() for d in dept_scope.split(",")]:
            return False
    return True


@app.get("/api/v1/mcp/tools")
async def list_mcp_tools(p: dict = Depends(current_user)):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id,name,category,description,tool_type,dept_scope,min_role,is_enabled,created_by,created_at "
            "FROM mcp_tools ORDER BY category,name"
        ).fetchall()
    user_role = p.get("role", "user")
    user_dept = p.get("department", "general")
    tools = []
    for r in rows:
        row = dict(r)
        if not row.get("is_enabled"):
            continue
        if not _can_run_tool(user_role, row["min_role"], user_dept, row.get("dept_scope")):
            continue
        with db_conn() as conn:
            cfg = conn.execute(
                "SELECT id FROM mcp_tool_configs WHERE tool_id=? AND dept_code=?",
                (row["id"], user_dept),
            ).fetchone()
        row["configured"] = cfg is not None
        tools.append(row)
    return {"tools": tools}


@app.post("/api/v1/mcp/tools")
async def create_mcp_tool(body: McpToolCreate, p: dict = Depends(current_user)):
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO mcp_tools (name,category,description,tool_type,dept_scope,min_role,is_enabled,created_by) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (body.name, body.category, body.description, body.tool_type,
             body.dept_scope, body.min_role, 1 if body.is_enabled else 0,
             p.get("username", "unknown")),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM mcp_tools ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {"status": "ok", "tool": dict(row)}


@app.patch("/api/v1/mcp/tools/{tool_id}")
async def update_mcp_tool(tool_id: int, body: McpToolUpdate, p: dict = Depends(current_user)):
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    fields, vals = [], []
    if body.name        is not None: fields.append("name=?");        vals.append(body.name)
    if body.description is not None: fields.append("description=?"); vals.append(body.description)
    if body.dept_scope  is not None: fields.append("dept_scope=?");  vals.append(body.dept_scope)
    if body.min_role    is not None: fields.append("min_role=?");    vals.append(body.min_role)
    if body.is_enabled  is not None: fields.append("is_enabled=?");  vals.append(1 if body.is_enabled else 0)
    if not fields:
        return {"status": "no-op"}
    vals.append(tool_id)
    with db_conn() as conn:
        conn.execute(f"UPDATE mcp_tools SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    return {"status": "ok"}


@app.delete("/api/v1/mcp/tools/{tool_id}")
async def delete_mcp_tool(tool_id: int, p: dict = Depends(current_user)):
    if p.get("role") != "root":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Root only")
    with db_conn() as conn:
        conn.execute("DELETE FROM mcp_tools WHERE id=?", (tool_id,))
        conn.commit()
    return {"status": "ok"}


@app.put("/api/v1/mcp/tools/{tool_id}/config")
async def set_mcp_tool_config(tool_id: int, body: McpConfigSet, p: dict = Depends(current_user)):
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    encrypted = _encrypt_config(body.config)
    who = p.get("username", "unknown")
    with db_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO mcp_tool_configs (tool_id,dept_code,config_json,configured_by) VALUES (?,?,?,?)",
            (tool_id, body.dept_code, encrypted, who),
        )
        conn.execute(
            "UPDATE mcp_tool_configs SET config_json=?,configured_by=?,configured_at=CURRENT_TIMESTAMP "
            "WHERE tool_id=? AND dept_code=?",
            (encrypted, who, tool_id, body.dept_code),
        )
        conn.commit()
    return {"status": "ok"}


@app.get("/api/v1/mcp/tools/{tool_id}/config/{dept_code}")
async def get_mcp_tool_config(tool_id: int, dept_code: str, p: dict = Depends(current_user)):
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    with db_conn() as conn:
        row = conn.execute(
            "SELECT config_json FROM mcp_tool_configs WHERE tool_id=? AND dept_code=?",
            (tool_id, dept_code),
        ).fetchone()
    if not row:
        return {"configured": False, "fields": {}}
    cfg = _decrypt_config(row["config_json"])
    _SENSITIVE = ("password", "key", "secret", "token", "webhook")
    redacted = {
        k: "***" if any(s in k.lower() for s in _SENSITIVE) else v
        for k, v in cfg.items()
    }
    return {"configured": True, "fields": redacted}


@app.post("/api/v1/mcp/run")
async def run_mcp_action(body: McpRunRequest, p: dict = Depends(current_user)):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM mcp_tools WHERE id=? AND is_enabled=1", (body.tool_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tool not found or disabled")
    tool = dict(row)
    user_dept = p.get("department", "general")

    if not _can_run_tool(p.get("role", "user"), tool["min_role"], user_dept, tool.get("dept_scope")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role for this tool")

    config: dict = {}
    if tool["tool_type"] in ("slack", "email"):
        with db_conn() as conn:
            cfg_row = conn.execute(
                "SELECT config_json FROM mcp_tool_configs WHERE tool_id=? AND dept_code=?",
                (body.tool_id, user_dept),
            ).fetchone()
        if cfg_row:
            config = _decrypt_config(cfg_row["config_json"])

    run_status, error_msg, result = "ok", None, {}
    try:
        from mcp_runners import dispatch as _mcp_dispatch
        result = _mcp_dispatch(tool["tool_type"], config, body.result_text, body.query, body.user_params)
    except Exception as exc:
        run_status = "error"
        error_msg  = str(exc)
        logger.error("MCP run error tool_id=%s type=%s: %s", body.tool_id, tool["tool_type"], exc)

    with db_conn() as conn:
        conn.execute(
            "INSERT INTO mcp_action_log (tool_id,user_id,dept_code,query_snippet,status,error_msg) "
            "VALUES (?,?,?,?,?,?)",
            (body.tool_id, p.get("user_id"), user_dept, body.query[:200], run_status, error_msg),
        )
        conn.commit()

    if run_status == "error":
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg or "Tool execution failed")

    return {"status": "ok", **result}


@app.get("/api/v1/mcp/logs")
async def get_mcp_logs(limit: int = 50, p: dict = Depends(current_user)):
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT l.id,l.tool_id,t.name as tool_name,l.user_id,l.dept_code,"
            "l.query_snippet,l.status,l.error_msg,l.ran_at "
            "FROM mcp_action_log l LEFT JOIN mcp_tools t ON l.tool_id=t.id "
            "ORDER BY l.ran_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return {"logs": [dict(r) for r in rows]}


# ═════════════════════════════════════════════════════════════════════════════
# RUN
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
