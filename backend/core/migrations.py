"""
Database migrations - creates all tables for SQLite and PostgreSQL.
For production, consider migrating to Alembic for versioned migrations.
"""

from __future__ import annotations

import sqlite3
import logging

from .config import DATABASE_URL, DB_PATH

logger = logging.getLogger(__name__)

# ─── Default Data ────────────────────────────────────────────────────────────
DEPARTMENTS = [
    ("hr",         "Human Resources",  "vaultmind-huron-hr-general",         "confidential"),
    ("legal",      "Legal",            "vaultmind-huron-legal-general",       "restricted"),
    ("finance",    "Finance",          "vaultmind-huron-finance-general",     "restricted"),
    ("clinical",   "Clinical",         "vaultmind-huron-clinical-general",    "hipaa_phi"),
    ("operations", "Operations",       "vaultmind-huron-operations-general",  "internal"),
    ("it",         "IT & Engineering", "vaultmind-huron-it-general",          "confidential"),
    ("marketing",  "Marketing",        "vaultmind-huron-marketing-general",   "internal"),
    ("external",   "External Sources", "vaultmind-huron-external-general",    "public"),
]

MCP_TOOLS = [
    ("Slack Notification", "communication", "Send result to a Slack channel",      "slack",         None, "user"),
    ("Email Report",       "communication", "Email result to a recipient",          "email",         None, "user"),
    ("PDF Report",         "report",        "Download result as a formatted PDF",   "pdf_report",    None, "user"),
    ("Data Analyzer",      "analysis",      "AI analysis of trends in the result",  "data_analyzer", None, "power_user"),
]


def run_migrations():
    """Run all database migrations."""
    if DATABASE_URL:
        _migrate_postgresql()
    else:
        _migrate_sqlite()


def _migrate_postgresql():
    """Create tables in PostgreSQL."""
    import psycopg2
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Users
    cur.execute("""
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
    
    # Departments
    cur.execute("""
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
    
    # Access Requests
    cur.execute("""
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
    
    # Audit Log
    cur.execute("""
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
    
    # Query Log
    cur.execute("""
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
    
    # Token Blacklist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            jti        TEXT PRIMARY KEY,
            expired_at TIMESTAMPTZ NOT NULL
        )
    """)
    
    # Feedback Log
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
    
    # Agent Runs
    cur.execute("""
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
    
    # Document Versions
    cur.execute("""
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
            is_latest      BOOLEAN DEFAULT TRUE,
            ingested_by    TEXT,
            ingested_at    TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(dept, doc_id, version)
        )
    """)
    
    # Conversations
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
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_msg ON conversation_messages(conversation_id, created_at ASC)")
    
    # MCP Tools
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mcp_tools (
            id          SERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL DEFAULT 'communication',
            description TEXT NOT NULL DEFAULT '',
            tool_type   TEXT NOT NULL,
            dept_scope  TEXT,
            min_role    TEXT NOT NULL DEFAULT 'user',
            is_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
            created_by  TEXT NOT NULL DEFAULT 'system',
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    
    cur.execute("""
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
    
    cur.execute("""
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
    
    # OIDC Role Mappings
    cur.execute("""
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
    
    _seed_data()
    logger.info("PostgreSQL migrations completed")


def _migrate_sqlite():
    """Create tables in SQLite."""
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
    
    c.execute("""
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
    
    c.execute("""
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
    
    c.execute("""
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
    
    c.execute("""
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
    
    c.execute("""
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
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated_at DESC)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_conv_msg ON conversation_messages(conversation_id, created_at ASC)")
    
    c.execute("""
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
    
    c.execute("""
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
    
    c.execute("""
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
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS oidc_role_mappings (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            provider     TEXT NOT NULL DEFAULT 'azure',
            ad_group     TEXT NOT NULL,
            huron_role   TEXT NOT NULL CHECK(huron_role IN ('root','dept_admin','power_user','user','viewer')),
            dept_code    TEXT,
            description  TEXT,
            created_by   TEXT NOT NULL DEFAULT 'system',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (provider, ad_group)
        )
    """)

    # ── Workday sync log ──────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS workday_sync_log (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at          TEXT    NOT NULL,
            finished_at         TEXT,
            status              TEXT    NOT NULL DEFAULT 'success',
            records_created     INTEGER NOT NULL DEFAULT 0,
            records_updated     INTEGER NOT NULL DEFAULT 0,
            records_deactivated INTEGER NOT NULL DEFAULT 0,
            error_message       TEXT,
            triggered_by        TEXT    NOT NULL DEFAULT 'scheduler'
        )
    """)

    # ── SharePoint sites registry ─────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS sharepoint_sites (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name      TEXT    NOT NULL,
            site_url       TEXT,
            graph_site_id  TEXT,
            dept_code      TEXT    NOT NULL,
            is_active      INTEGER NOT NULL DEFAULT 1,
            last_synced_at TEXT,
            created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (site_name)
        )
    """)

    # ── SharePoint sync log ───────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS sharepoint_sync_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id      TEXT    NOT NULL,
            site_name    TEXT    NOT NULL,
            dept_code    TEXT    NOT NULL,
            started_at   TEXT    NOT NULL,
            finished_at  TEXT,
            status       TEXT    NOT NULL DEFAULT 'success',
            ingested     INTEGER NOT NULL DEFAULT 0,
            failed       INTEGER NOT NULL DEFAULT 0,
            error_detail TEXT,
            triggered_by TEXT    NOT NULL DEFAULT 'scheduler'
        )
    """)

    # ── Add new columns to users (safe for existing DBs) ─────────────────────
    for col_sql in (
        "ALTER TABLE users ADD COLUMN auth_method  TEXT NOT NULL DEFAULT 'local'",
        "ALTER TABLE users ADD COLUMN workday_id   TEXT",
        "ALTER TABLE users ADD COLUMN employee_id  TEXT",
    ):
        try:
            c.execute(col_sql)
        except Exception:
            pass  # column already exists

    conn.commit()
    conn.close()

    _seed_data()
    _seed_sharepoint_demo_sites()
    logger.info("SQLite migrations completed")


def _seed_sharepoint_demo_sites():
    """Insert demo SharePoint sites if the table is empty."""
    from .database import DBConn
    with DBConn() as conn:
        if conn.execute("SELECT COUNT(*) FROM sharepoint_sites").fetchone()[0] == 0:
            for name, dept in (
                ("HR Documents",       "hr"),
                ("Legal Documents",    "legal"),
                ("Clinical Documents", "clinical"),
                ("Finance Documents",  "finance"),
            ):
                conn.execute(
                    "INSERT OR IGNORE INTO sharepoint_sites (site_name, dept_code) VALUES (?, ?)",
                    (name, dept),
                )
            conn.commit()


def _seed_data():
    """Seed initial data (root user, departments, MCP tools)."""
    import bcrypt
    from .database import DBConn
    
    with DBConn() as conn:
        # Seed root user
        if not conn.execute("SELECT id FROM users WHERE role=?", ("root",)).fetchone():
            ph = bcrypt.hashpw(b"HuronRoot2026!", bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username,email,full_name,password_hash,role,department) "
                "VALUES (?,?,?,?,?,?)",
                ("root", "root@huron-vaultmind.ai", "Root Administrator", ph, "root", "all"),
            )
            logger.info("Root user created — username: root")
        
        # Seed departments
        for code, name, ns, cls in DEPARTMENTS:
            if not conn.execute("SELECT id FROM departments WHERE code=?", (code,)).fetchone():
                conn.execute(
                    "INSERT INTO departments (code,display_name,namespace,classification) VALUES (?,?,?,?)",
                    (code, name, ns, cls),
                )
        
        # Seed MCP tools
        if not conn.execute("SELECT id FROM mcp_tools LIMIT 1").fetchone():
            for name, cat, desc, ttype, scope, min_role in MCP_TOOLS:
                conn.execute(
                    "INSERT INTO mcp_tools (name,category,description,tool_type,dept_scope,min_role) "
                    "VALUES (?,?,?,?,?,?)",
                    (name, cat, desc, ttype, scope, min_role),
                )
        
        conn.commit()
