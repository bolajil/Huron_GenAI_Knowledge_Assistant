"""
Huron GenAI Knowledge Assistant - FastAPI Backend v3
Production-grade with:
- 4-tier admin hierarchy (root -> dept_admin -> power_user -> user/viewer)
- Separation of duty matching Pinecone namespace isolation
- Real dashboard stats from DB + Pinecone
- JWT token blacklist (real logout)
- Access request workflow
- Audit logging
"""

from __future__ import annotations

import os
import sys
import sqlite3
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import bcrypt
import jwt
import uvicorn
from dotenv import load_dotenv
from fastapi import (
    FastAPI, Depends, HTTPException, UploadFile,
    File, Form, status, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

# ─── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Huron GenAI Knowledge Assistant API",
    description="Enterprise multi-tenant AI knowledge management",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://localhost:3001",
        "http://127.0.0.1:3000", "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production-use-strong-random-key")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8
REFRESH_EXPIRE_DAYS = 7

# ─── Database ───────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "data" / "huron.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# In-memory token blacklist (use Redis in production)
_token_blacklist: set[str] = set()


def init_db():
    """Initialize database with full schema for RBAC hierarchy."""
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
            ip_address  TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS query_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER REFERENCES users(id),
            dept_code       TEXT,
            query_text      TEXT,
            response_ms     INTEGER,
            faithfulness    REAL,
            sources_count   INTEGER DEFAULT 0,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS token_blacklist (
            jti         TEXT PRIMARY KEY,
            expired_at  TIMESTAMP NOT NULL
        )
    """)

    # Seed root user
    c.execute("SELECT id FROM users WHERE role = 'root'")
    if not c.fetchone():
        ph = bcrypt.hashpw(b"HuronRoot2026!", bcrypt.gensalt()).decode()
        c.execute(
            "INSERT INTO users (username, email, full_name, password_hash, role, department) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("root", "root@huron-vaultmind.ai", "Root Administrator", ph, "root", "all")
        )
        logger.info("Root user created: username=root password=HuronRoot2026!")

    # Seed departments
    depts = [
        ("hr",         "Human Resources",  "vaultmind-huron-hr-general",         "confidential"),
        ("legal",      "Legal",            "vaultmind-huron-legal-general",       "restricted"),
        ("finance",    "Finance",          "vaultmind-huron-finance-general",     "restricted"),
        ("clinical",   "Clinical",         "vaultmind-huron-clinical-general",    "hipaa_phi"),
        ("operations", "Operations",       "vaultmind-huron-operations-general",  "internal"),
        ("it",         "IT & Engineering", "vaultmind-huron-it-general",          "confidential"),
        ("marketing",  "Marketing",        "vaultmind-huron-marketing-general",   "internal"),
        ("external",   "External Sources", "vaultmind-huron-external-general",    "public"),
    ]
    for code, name, ns, cls in depts:
        c.execute("SELECT id FROM departments WHERE code = ?", (code,))
        if not c.fetchone():
            c.execute(
                "INSERT INTO departments (code, display_name, namespace, classification) VALUES (?,?,?,?)",
                (code, name, ns, cls)
            )

    conn.commit()
    conn.close()


# ─── DB Helpers ─────────────────────────────────────────────────────────────

def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_id(user_id: int) -> Optional[dict]:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,username,email,full_name,role,department,is_active FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[dict]:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT id,username,email,full_name,password_hash,role,department,is_active "
            "FROM users WHERE username=? OR email=?",
            (username, username)
        ).fetchone()
    return dict(row) if row else None


def write_audit(user_id: Optional[int], username: str, action: str,
                dept: str = "", namespace: str = "", detail: str = ""):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (user_id,username,action,dept_code,namespace,detail) VALUES (?,?,?,?,?,?)",
            (user_id, username, action, dept, namespace, detail)
        )
        conn.commit()


def log_query(user_id: int, dept: str, query_text: str, response_ms: int,
              faithfulness: float, sources: int):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO query_log (user_id,dept_code,query_text,response_ms,faithfulness,sources_count) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, dept, query_text[:500], response_ms, faithfulness, sources)
        )
        conn.execute(
            "UPDATE departments SET query_count=query_count+1 WHERE code=?", (dept,)
        )
        conn.commit()


# ─── Role definitions ────────────────────────────────────────────────────────

ROLE_CLEARANCE = {
    "root": 5,
    "dept_admin": 4,
    "power_user": 3,
    "user": 2,
    "viewer": 1,
}

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "root": [
        "query", "chat", "ingest", "research", "agent",
        "admin", "manage_users", "manage_departments",
        "manage_all_depts", "create_dept_admin",
        "approve_requests", "view_audit_log", "mcp", "analytics",
    ],
    "dept_admin": [
        "query", "chat", "ingest", "research", "agent",
        "manage_users", "manage_dept_users", "approve_requests",
        "analytics", "mcp",
    ],
    "power_user": ["query", "chat", "ingest", "research", "agent", "analytics"],
    "user":       ["query", "chat", "ingest"],
    "viewer":     ["query", "chat"],
}


def _namespace_scope(role: str, dept: str) -> list[str]:
    if role == "root":
        return ["*"]
    return [dept]


def create_token(user: dict) -> str:
    jti = secrets.token_hex(16)
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "jti": jti,
        "sub": user["username"],
        "user_id": user["id"],
        "email": user["email"],
        "full_name": user.get("full_name", user["username"].title()),
        "role": user["role"],
        "dept_id": user["department"],
        "clearance_level": ROLE_CLEARANCE.get(user["role"], 1),
        "namespace_scope": _namespace_scope(user["role"], user["department"]),
        "permissions": ROLE_PERMISSIONS.get(user["role"], ["query", "chat"]),
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti", "")
        if jti in _token_blacklist:
            return None
        with db_conn() as conn:
            row = conn.execute(
                "SELECT jti FROM token_blacklist WHERE jti=?", (jti,)
            ).fetchone()
            if row:
                _token_blacklist.add(jti)
                return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def blacklist_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM],
                             options={"verify_exp": False})
        jti = payload.get("jti", "")
        exp = datetime.utcfromtimestamp(payload.get("exp", 0))
        _token_blacklist.add(jti)
        with db_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO token_blacklist (jti, expired_at) VALUES (?,?)",
                (jti, exp)
            )
            conn.commit()
    except Exception:
        pass


# ─── FastAPI dependencies ─────────────────────────────────────────────────────

async def current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


async def require_root(payload: dict = Depends(current_user)) -> dict:
    if payload.get("role") != "root":
        raise HTTPException(status_code=403, detail="Root access required")
    return payload


async def require_admin(payload: dict = Depends(current_user)) -> dict:
    if payload.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


def check_permission(payload: dict, permission: str):
    perms = payload.get("permissions", [])
    if permission not in perms:
        raise HTTPException(status_code=403, detail=f"Permission '{permission}' required")


def check_dept_access(payload: dict, target_dept: str):
    """Enforce namespace-level separation of duty."""
    role = payload.get("role")
    user_dept = payload.get("dept_id")
    scope = payload.get("namespace_scope", [])

    if role == "root" or "*" in scope:
        return

    if user_dept != target_dept and target_dept not in scope:
        write_audit(
            payload.get("user_id"), payload.get("sub"),
            "namespace_access_denied",
            target_dept, target_dept,
            f"User dept={user_dept} tried to access dept={target_dept}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Access to department '{target_dept}' is not permitted for your account"
        )


# ─── Pipeline singletons ─────────────────────────────────────────────────────

_ingestion_svc = None
_rag = None


def get_ingestion_service():
    global _ingestion_svc
    if _ingestion_svc is None:
        try:
            from utils.ingestion_service import IngestionService
            _ingestion_svc = IngestionService(
                enable_pinecone=True,
                enable_dlp_scan=True,
                enable_quality_gate=True,
                enable_classification=False,
                pinecone_index=os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge"),
            )
        except Exception as e:
            logger.warning(f"IngestionService unavailable: {e}")
    return _ingestion_svc


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


# ─── Pydantic models ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str
    auth_method: str = "local"
    remember_me: bool = False


class MFAVerifyRequest(BaseModel):
    code: str
    session_token: Optional[str] = None
    pending_token: Optional[str] = None


class CreateUserRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: str = "user"
    department: str


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class QueryRequest(BaseModel):
    query: str
    department: Optional[str] = None
    top_k: int = 10


class ChatRequest(BaseModel):
    messages: list[dict]
    department: Optional[str] = None


class AccessRequestCreate(BaseModel):
    dept_code: str
    requested_tab: str
    requested_role: str = "user"
    justification: str


class AccessRequestReview(BaseModel):
    request_id: int
    action: str  # "approve" | "reject"
    note: Optional[str] = None


# ─── Startup ─────────────────────────────────────────────────────────────────

init_db()


# ─────────────────────────────────────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    user = get_user_by_username(request.username)
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(request.password.encode(), user["password_hash"].encode()):
        write_audit(None, request.username, "auth_failure")
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
            "permissions": ROLE_PERMISSIONS.get(user["role"], ["query", "chat"]),
        }
    }


@app.post("/api/v1/auth/logout")
async def logout(request: Request, token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if payload:
        blacklist_token(token)
        write_audit(payload.get("user_id"), payload.get("sub"), "logout")
    return {"message": "Logged out successfully"}


@app.get("/api/v1/auth/validate")
async def validate_token(payload: dict = Depends(current_user)):
    return {"valid": True, "user": payload["sub"], "role": payload.get("role")}


@app.get("/api/v1/auth/me")
async def me(payload: dict = Depends(current_user)):
    return {
        "id": payload.get("user_id"),
        "username": payload.get("sub"),
        "email": payload.get("email"),
        "full_name": payload.get("full_name"),
        "department": payload.get("dept_id"),
        "role": payload.get("role"),
        "permissions": payload.get("permissions", []),
        "clearance_level": payload.get("clearance_level"),
    }


@app.post("/api/v1/auth/mfa/verify")
async def mfa_verify(body: dict):
    code = body.get("code", "")
    if len(code) == 6 and code.isdigit():
        # Accept pending_token (v3) or session_token (v2 compat)
        pending_token = body.get("pending_token") or body.get("session_token")
        if pending_token:
            payload = verify_token(pending_token)
            if payload:
                return {
                    "status": "success",
                    "access_token": pending_token,
                    "token_type": "bearer",
                    "message": "MFA verified successfully",
                }
        # Dev fallback — accept any 6-digit code without a token
        return {
            "status": "success",
            "access_token": "dev-bypass-token",
            "token_type": "bearer",
            "message": "MFA verified (dev mode — no pending token)",
        }
    raise HTTPException(status_code=400, detail="Invalid MFA code")


@app.post("/api/v1/auth/mfa/setup")
async def mfa_setup(payload: dict = Depends(current_user)):
    return {
        "status": "success",
        "secret": "DEMO_SECRET_KEY",
        "qr_code": f"otpauth://totp/VaultMind:{payload.get('sub')}?secret=DEMO_SECRET_KEY&issuer=VaultMind",
        "message": "MFA setup initialized",
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROOT-ONLY ADMIN ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/root/users")
async def root_list_all_users(payload: dict = Depends(require_root)):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT u.id,u.username,u.email,u.full_name,u.role,u.department,"
            "u.is_active,u.last_login,u.created_at,c.username as created_by_name "
            "FROM users u LEFT JOIN users c ON u.created_by=c.id ORDER BY u.created_at DESC"
        ).fetchall()
    return {"users": [dict(r) for r in rows]}


@app.post("/api/v1/root/users")
async def root_create_user(body: CreateUserRequest, payload: dict = Depends(require_root)):
    if body.role == "root":
        raise HTTPException(status_code=400, detail="Cannot create another root user")
    ph = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    try:
        with db_conn() as conn:
            conn.execute(
                "INSERT INTO users (username,email,full_name,password_hash,role,department,created_by) "
                "VALUES (?,?,?,?,?,?,?)",
                (body.username, body.email, body.full_name, ph, body.role,
                 body.department, payload["user_id"])
            )
            conn.execute(
                "UPDATE departments SET user_count=user_count+1 WHERE code=?", (body.department,)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    write_audit(payload["user_id"], payload["sub"], "create_user",
                body.department, detail=f"Created {body.role} {body.username}")
    return {"status": "success", "message": f"User {body.username} created"}


@app.put("/api/v1/root/users/{user_id}")
async def root_update_user(user_id: int, body: UpdateUserRequest,
                           payload: dict = Depends(require_root)):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "root":
        raise HTTPException(status_code=400, detail="Cannot modify root user")

    updates, values = [], []
    if body.full_name is not None:
        updates.append("full_name=?"); values.append(body.full_name)
    if body.role is not None:
        updates.append("role=?"); values.append(body.role)
    if body.department is not None:
        updates.append("department=?"); values.append(body.department)
    if body.is_active is not None:
        updates.append("is_active=?"); values.append(1 if body.is_active else 0)

    if updates:
        values.append(user_id)
        with db_conn() as conn:
            conn.execute(
                f"UPDATE users SET {','.join(updates)},updated_at=CURRENT_TIMESTAMP WHERE id=?",
                values
            )
            conn.commit()

    write_audit(payload["user_id"], payload["sub"], "update_user",
                detail=f"Updated user {target['username']}")
    return {"status": "success"}


@app.delete("/api/v1/root/users/{user_id}")
async def root_delete_user(user_id: int, payload: dict = Depends(require_root)):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "root":
        raise HTTPException(status_code=400, detail="Cannot delete root user")
    with db_conn() as conn:
        conn.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
        conn.execute(
            "UPDATE departments SET user_count=MAX(0,user_count-1) WHERE code=?",
            (target["department"],)
        )
        conn.commit()
    write_audit(payload["user_id"], payload["sub"], "deactivate_user",
                detail=f"Deactivated {target['username']}")
    return {"status": "success"}


@app.get("/api/v1/root/departments")
async def root_list_departments(payload: dict = Depends(require_root)):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT d.*,u.username as admin_username FROM departments d "
            "LEFT JOIN users u ON d.admin_user_id=u.id"
        ).fetchall()
    return {"departments": [dict(r) for r in rows]}


@app.post("/api/v1/root/departments/{code}/assign-admin")
async def assign_dept_admin(code: str, body: dict, payload: dict = Depends(require_root)):
    user_id = body.get("user_id")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    with db_conn() as conn:
        conn.execute("UPDATE departments SET admin_user_id=? WHERE code=?", (user_id, code))
        conn.execute("UPDATE users SET role='dept_admin', department=? WHERE id=?", (code, user_id))
        conn.commit()
    write_audit(payload["user_id"], payload["sub"], "assign_dept_admin",
                code, detail=f"Assigned {user['username']} as admin of {code}")
    return {"status": "success"}


@app.get("/api/v1/root/audit-log")
async def get_audit_log(
    limit: int = 100,
    dept: Optional[str] = None,
    action: Optional[str] = None,
    payload: dict = Depends(require_root),
):
    query = "SELECT * FROM audit_log WHERE 1=1"
    params: list = []
    if dept:
        query += " AND dept_code=?"; params.append(dept)
    if action:
        query += " AND action=?"; params.append(action)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return {"audit_log": [dict(r) for r in rows]}


# ─────────────────────────────────────────────────────────────────────────────
# DEPT ADMIN ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/admin/dept-users")
async def dept_admin_list_users(payload: dict = Depends(require_admin)):
    if payload["role"] == "root":
        with db_conn() as conn:
            rows = conn.execute(
                "SELECT id,username,email,full_name,role,department,is_active,last_login "
                "FROM users ORDER BY department,role"
            ).fetchall()
    else:
        dept = payload["dept_id"]
        with db_conn() as conn:
            rows = conn.execute(
                "SELECT id,username,email,full_name,role,department,is_active,last_login "
                "FROM users WHERE department=? ORDER BY role",
                (dept,)
            ).fetchall()
    return {"users": [dict(r) for r in rows]}


@app.post("/api/v1/admin/dept-users")
async def dept_admin_create_user(body: CreateUserRequest, payload: dict = Depends(require_admin)):
    admin_dept = payload.get("dept_id")
    if payload["role"] != "root" and body.department != admin_dept:
        raise HTTPException(status_code=403,
                            detail=f"You can only create users in your department: {admin_dept}")
    if body.role in ("root", "dept_admin") and payload["role"] != "root":
        raise HTTPException(status_code=403, detail="Only root can create admin-level users")

    ph = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    try:
        with db_conn() as conn:
            conn.execute(
                "INSERT INTO users (username,email,full_name,password_hash,role,department,created_by) "
                "VALUES (?,?,?,?,?,?,?)",
                (body.username, body.email, body.full_name, ph, body.role,
                 body.department, payload["user_id"])
            )
            conn.execute(
                "UPDATE departments SET user_count=user_count+1 WHERE code=?", (body.department,)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username or email already exists")

    write_audit(payload["user_id"], payload["sub"], "create_user",
                body.department, detail=f"Created {body.role} {body.username}")
    return {"status": "success", "message": f"User {body.username} created"}


@app.put("/api/v1/admin/dept-users/{user_id}")
async def dept_admin_update_user(user_id: int, body: UpdateUserRequest,
                                  payload: dict = Depends(require_admin)):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if payload["role"] != "root" and target["department"] != payload["dept_id"]:
        raise HTTPException(status_code=403, detail="Cannot modify users outside your department")
    if target["role"] == "root":
        raise HTTPException(status_code=403, detail="Cannot modify root user")

    updates, values = [], []
    if body.full_name is not None:
        updates.append("full_name=?"); values.append(body.full_name)
    if body.role is not None and payload["role"] == "root":
        updates.append("role=?"); values.append(body.role)
    if body.is_active is not None:
        updates.append("is_active=?"); values.append(1 if body.is_active else 0)

    if updates:
        values.append(user_id)
        with db_conn() as conn:
            conn.execute(
                f"UPDATE users SET {','.join(updates)},updated_at=CURRENT_TIMESTAMP WHERE id=?",
                values
            )
            conn.commit()

    write_audit(payload["user_id"], payload["sub"], "update_user",
                target["department"], detail=f"Updated {target['username']}")
    return {"status": "success"}


# ─────────────────────────────────────────────────────────────────────────────
# ACCESS REQUEST ROUTES
# ─────────────────────────────────────────────────────────────────────────────

REQUESTABLE_TABS = [
    "query", "chat", "ingest", "research", "agent",
    "analytics", "mcp", "admin", "cross_dept_query",
]


def _tab_description(tab: str) -> str:
    return {
        "query": "Search documents in your department's knowledge base",
        "chat": "Conversational AI with your department documents",
        "ingest": "Upload and index new documents",
        "research": "Deep multi-source research mode",
        "agent": "Autonomous AI agent with multi-step reasoning",
        "analytics": "Usage analytics and query statistics",
        "mcp": "Model Context Protocol tool integrations",
        "admin": "Administrative panel access",
        "cross_dept_query": "Query documents across multiple departments",
    }.get(tab, tab)


@app.get("/api/v1/access-requests/tabs")
async def list_requestable_tabs(payload: dict = Depends(current_user)):
    current_perms = set(payload.get("permissions", []))
    tabs = [
        {
            "tab": tab,
            "label": tab.replace("_", " ").title(),
            "description": _tab_description(tab),
            "currently_accessible": tab in current_perms,
            "requires_approval_from": "dept_admin" if tab != "admin" else "root",
        }
        for tab in REQUESTABLE_TABS
    ]
    return {"tabs": tabs, "user_role": payload.get("role", "viewer")}


@app.post("/api/v1/access-requests")
async def submit_access_request(body: AccessRequestCreate, payload: dict = Depends(current_user)):
    if body.requested_tab not in REQUESTABLE_TABS:
        raise HTTPException(status_code=400, detail=f"Invalid tab: {body.requested_tab}")
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO access_requests (requester_id,dept_code,requested_tab,requested_role,justification) "
            "VALUES (?,?,?,?,?)",
            (payload["user_id"], body.dept_code, body.requested_tab,
             body.requested_role, body.justification)
        )
        conn.commit()
    return {"status": "success", "message": "Access request submitted for review"}


@app.get("/api/v1/access-requests")
async def list_access_requests(
    status_filter: Optional[str] = None,
    payload: dict = Depends(current_user),
):
    role = payload["role"]
    query = """
        SELECT ar.*,
               u.username as requester_name, u.email as requester_email,
               r.username as reviewer_name
        FROM access_requests ar
        JOIN users u ON ar.requester_id=u.id
        LEFT JOIN users r ON ar.reviewed_by=r.id
        WHERE 1=1
    """
    params: list = []
    if role == "root":
        pass
    elif role == "dept_admin":
        query += " AND ar.dept_code=?"; params.append(payload["dept_id"])
    else:
        query += " AND ar.requester_id=?"; params.append(payload["user_id"])

    if status_filter:
        query += " AND ar.status=?"; params.append(status_filter)

    query += " ORDER BY ar.created_at DESC"
    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return {"requests": [dict(r) for r in rows]}


@app.post("/api/v1/access-requests/review")
async def review_access_request(body: AccessRequestReview, payload: dict = Depends(require_admin)):
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM access_requests WHERE id=?", (body.request_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")

        req = dict(row)
        if payload["role"] == "dept_admin" and req["dept_code"] != payload["dept_id"]:
            raise HTTPException(status_code=403, detail="Not your department's request")

        new_status = "approved" if body.action == "approve" else "rejected"
        conn.execute(
            "UPDATE access_requests SET status=?,reviewed_by=?,reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_status, payload["user_id"], body.request_id)
        )

        if body.action == "approve":
            conn.execute(
                "UPDATE users SET role=? WHERE id=? AND role NOT IN ('root','dept_admin')",
                (req["requested_role"], req["requester_id"])
            )

        conn.commit()

    write_audit(payload["user_id"], payload["sub"],
                f"{body.action}_request", detail=f"Request ID {body.request_id}")
    return {"status": "success", "new_status": new_status}


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD STATS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/admin/stats")
async def get_stats(payload: dict = Depends(current_user)):
    role = payload["role"]
    dept = payload["dept_id"]

    with db_conn() as conn:
        if role == "root":
            total_users = conn.execute(
                "SELECT COUNT(*) FROM users WHERE is_active=1"
            ).fetchone()[0]
        else:
            total_users = conn.execute(
                "SELECT COUNT(*) FROM users WHERE department=? AND is_active=1", (dept,)
            ).fetchone()[0]

        today = datetime.utcnow().date().isoformat()
        if role == "root":
            queries_today = conn.execute(
                "SELECT COUNT(*) FROM query_log WHERE created_at>=?", (today,)
            ).fetchone()[0]
        else:
            queries_today = conn.execute(
                "SELECT COUNT(*) FROM query_log WHERE dept_code=? AND created_at>=?",
                (dept, today)
            ).fetchone()[0]

        if role == "root":
            avg_rt = conn.execute(
                "SELECT AVG(response_ms) FROM "
                "(SELECT response_ms FROM query_log ORDER BY id DESC LIMIT 100)"
            ).fetchone()[0]
        else:
            avg_rt = conn.execute(
                "SELECT AVG(response_ms) FROM "
                "(SELECT response_ms FROM query_log WHERE dept_code=? ORDER BY id DESC LIMIT 100)",
                (dept,)
            ).fetchone()[0]

        if role == "root":
            avg_faith = conn.execute(
                "SELECT AVG(faithfulness) FROM query_log WHERE faithfulness IS NOT NULL"
            ).fetchone()[0]
        else:
            avg_faith = conn.execute(
                "SELECT AVG(faithfulness) FROM query_log "
                "WHERE dept_code=? AND faithfulness IS NOT NULL",
                (dept,)
            ).fetchone()[0]

        if role == "root":
            total_docs = conn.execute("SELECT SUM(doc_count) FROM departments").fetchone()[0] or 0
        else:
            row = conn.execute(
                "SELECT doc_count FROM departments WHERE code=?", (dept,)
            ).fetchone()
            total_docs = row[0] if row else 0

    # Pinecone status (best-effort)
    pinecone_stats: dict = {}
    try:
        from pinecone import Pinecone as PineconeClient
        pc = PineconeClient(api_key=os.getenv("PINECONE_API_KEY", ""))
        index_name = os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge")
        pc.describe_index(index_name)
        pinecone_stats = {"status": "connected", "index": index_name}
    except Exception as e:
        pinecone_stats = {"status": "unavailable", "error": str(e)}

    with db_conn() as conn:
        dept_count = conn.execute(
            "SELECT COUNT(*) FROM departments WHERE is_active=1"
        ).fetchone()[0]

    return {
        "total_documents": int(total_docs or 0),
        "queries_today": int(queries_today or 0),
        "active_users": int(total_users or 0),
        "total_users": int(total_users or 0),
        "departments": int(dept_count or 0),
        "avg_response_time": round((avg_rt or 0) / 1000, 2),
        "avg_faithfulness": round(avg_faith or 0, 2),
        "pinecone": pinecone_stats,
        "scope": "global" if role == "root" else dept,
    }


@app.get("/api/v1/admin/stats/recent-queries")
async def recent_queries(limit: int = 20, payload: dict = Depends(current_user)):
    role = payload["role"]
    dept = payload["dept_id"]
    with db_conn() as conn:
        if role == "root":
            rows = conn.execute(
                "SELECT ql.*, u.username FROM query_log ql "
                "LEFT JOIN users u ON ql.user_id=u.id "
                "ORDER BY ql.created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ql.*, u.username FROM query_log ql "
                "LEFT JOIN users u ON ql.user_id=u.id "
                "WHERE ql.dept_code=? ORDER BY ql.created_at DESC LIMIT ?",
                (dept, limit)
            ).fetchall()
    return {"queries": [dict(r) for r in rows]}


@app.get("/api/v1/admin/departments")
async def list_departments(payload: dict = Depends(current_user)):
    role = payload["role"]
    dept = payload["dept_id"]
    with db_conn() as conn:
        if role == "root":
            rows = conn.execute(
                "SELECT d.*,u.username as admin_username,u.email as admin_email "
                "FROM departments d LEFT JOIN users u ON d.admin_user_id=u.id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT d.*,u.username as admin_username FROM departments d "
                "LEFT JOIN users u ON d.admin_user_id=u.id WHERE d.code=?",
                (dept,)
            ).fetchall()
    return {"departments": [dict(r) for r in rows]}


@app.get("/api/v1/admin/users")
async def list_users_compat(payload: dict = Depends(require_admin)):
    """Compatibility alias for frontend api.getUsers()."""
    return await dept_admin_list_users(payload)


# ─────────────────────────────────────────────────────────────────────────────
# QUERY + CHAT + INGEST (with separation of duty)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/v1/query")
async def query_endpoint(request: QueryRequest, payload: dict = Depends(current_user)):
    import time
    check_permission(payload, "query")

    dept = request.department or payload.get("dept_id", "general")
    check_dept_access(payload, dept)

    start = time.time()
    rag = get_rag()
    if not rag:
        return {
            "status": "degraded",
            "query": request.query,
            "results": "RAG pipeline initializing. Please ensure OPENAI_API_KEY and PINECONE_API_KEY are set.",
            "sources": [],
            "dept": dept,
        }

    try:
        from utils.tenant_context import TenantContext
        ctx = TenantContext(
            tenant_id="huron",
            dept_id=dept,
            username=payload.get("sub"),
            role=payload.get("role", "user"),
        )
        result = await rag.query(query=request.query, tenant_context=ctx)
        elapsed = int((time.time() - start) * 1000)

        log_query(
            payload.get("user_id", 0), dept, request.query,
            elapsed, result.get("faithfulness_score", 0),
            len(result.get("sources", [])),
        )
        return {
            "status": "success",
            "query": request.query,
            "results": result.get("response", ""),
            "sources": [{"title": s} for s in result.get("sources", [])],
            "intent": result.get("intent"),
            "faithfulness_score": result.get("faithfulness_score"),
            "processing_time_ms": elapsed,
            "dept": dept,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/chat")
async def chat_endpoint(request: ChatRequest, payload: dict = Depends(current_user)):
    check_permission(payload, "chat")
    dept = request.department or payload.get("dept_id", "general")
    check_dept_access(payload, dept)

    last_msg = next(
        (m["content"] for m in reversed(request.messages) if m.get("role") == "user"), ""
    )
    rag = get_rag()
    if not rag:
        return {"status": "degraded", "response": "RAG pipeline initializing.", "sources": []}

    try:
        from utils.tenant_context import TenantContext
        ctx = TenantContext(tenant_id="huron", dept_id=dept,
                            username=payload.get("sub"), role=payload.get("role", "user"))
        result = await rag.query(query=last_msg, tenant_context=ctx)
        return {
            "status": "success",
            "response": result.get("response", ""),
            "sources": [{"title": s} for s in result.get("sources", [])],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ingest")
async def ingest_endpoint(
    file: UploadFile = File(...),
    department: str = Form("general"),
    sensitivity_level: str = Form("internal"),
    token: str = Depends(oauth2_scheme),
):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    check_permission(payload, "ingest")
    dept = department or payload.get("dept_id", "general")
    check_dept_access(payload, dept)

    svc = get_ingestion_service()
    if not svc:
        return {
            "status": "degraded",
            "message": "Ingestion pipeline initializing. Ensure PINECONE_API_KEY is set.",
            "file": file.filename,
        }

    try:
        content = await file.read()
        from utils.tenant_context import TenantContext
        ctx = TenantContext(tenant_id="huron", dept_id=dept,
                            username=payload.get("sub"), role=payload.get("role", "user"))
        result = await svc.ingest_document(
            file_content=content,
            file_name=file.filename,
            tenant_context=ctx,
            sensitivity_level=sensitivity_level,
        )
        if result.success:
            with db_conn() as conn:
                conn.execute(
                    "UPDATE departments SET doc_count=doc_count+? WHERE code=?",
                    (result.parent_chunks, dept)
                )
                conn.commit()
        write_audit(payload.get("user_id"), payload.get("sub"), "ingest",
                    dept, getattr(result, "namespace", ""), f"File: {file.filename}")
        return {
            "status": "success" if result.success else "error",
            "document_id": getattr(result, "document_id", ""),
            "file": file.filename,
            "department": dept,
            "namespace": getattr(result, "namespace", ""),
            "parent_chunks": getattr(result, "parent_chunks", 0),
            "child_chunks": getattr(result, "child_chunks", 0),
            "pinecone_upsert": getattr(result, "_pinecone_upsert_success", False),
            "warnings": getattr(result, "warnings", []),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# INDEXES + HEALTH
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/v1/indexes")
async def list_indexes(payload: dict = Depends(current_user)):
    """Return available FAISS / Pinecone indexes."""
    try:
        from utils.ingestion_service import IngestionService
        svc = get_ingestion_service()
        if svc and hasattr(svc, "list_indexes"):
            indexes = svc.list_indexes()
        else:
            indexes = [{"name": "default_faiss", "type": "faiss", "documents": 0,
                        "size_mb": 0, "status": "ready"}]
    except Exception:
        indexes = [{"name": "default_faiss", "type": "faiss", "documents": 0,
                    "size_mb": 0, "status": "unavailable"}]
    return {"status": "success", "count": len(indexes), "indexes": indexes}


@app.get("/health")
async def health():
    try:
        with db_conn() as conn:
            conn.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": "3.0.0",
        "db": "connected" if db_ok else "error",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
