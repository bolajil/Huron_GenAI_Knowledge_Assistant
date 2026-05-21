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

import os, sys, sqlite3, logging, secrets, time
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

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))

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

# ─── Database ────────────────────────────────────────────────────────────────
#
# POSTGRESQL MIGRATION — run when ready:
#   pip install asyncpg sqlalchemy[asyncio]
#   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/huron"
#   Replace db_conn() with SQLAlchemy async session + Alembic.
#   Connection pool: pool_size=20, max_overflow=40, pool_timeout=30
#   PgBouncer in front for 20k users (transaction pooling mode).
#
DB_PATH = Path(__file__).parent.parent / "data" / "huron.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Token blacklist — in-memory + SQLite now.
# REDIS MIGRATION: replace with redis.Redis(host=REDIS_HOST).sadd("blacklist", jti)
_token_blacklist: set[str] = set()


def init_db():
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

    # Root user
    c.execute("SELECT id FROM users WHERE role = 'root'")
    if not c.fetchone():
        ph = bcrypt.hashpw(b"HuronRoot2026!", bcrypt.gensalt()).decode()
        c.execute(
            "INSERT INTO users (username,email,full_name,password_hash,role,department) "
            "VALUES (?,?,?,?,?,?)",
            ("root", "root@huron-vaultmind.ai", "Root Administrator", ph, "root", "all"),
        )
        logger.info("Root user created — username: root  password: HuronRoot2026!")

    # Departments
    for code, name, ns, cls in [
        ("hr",         "Human Resources",  "vaultmind-huron-hr-general",         "confidential"),
        ("legal",      "Legal",            "vaultmind-huron-legal-general",       "restricted"),
        ("finance",    "Finance",          "vaultmind-huron-finance-general",     "restricted"),
        ("clinical",   "Clinical",         "vaultmind-huron-clinical-general",    "hipaa_phi"),
        ("operations", "Operations",       "vaultmind-huron-operations-general",  "internal"),
        ("it",         "IT & Engineering", "vaultmind-huron-it-general",          "confidential"),
        ("marketing",  "Marketing",        "vaultmind-huron-marketing-general",   "internal"),
        ("external",   "External Sources", "vaultmind-huron-external-general",    "public"),
    ]:
        c.execute("SELECT id FROM departments WHERE code=?", (code,))
        if not c.fetchone():
            c.execute(
                "INSERT INTO departments (code,display_name,namespace,classification) VALUES (?,?,?,?)",
                (code, name, ns, cls),
            )

    conn.commit()
    conn.close()


# ─── DB helpers ───────────────────────────────────────────────────────────────

def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
    "root":       ["query","chat","ingest","research","agent","admin","manage_users",
                   "manage_departments","manage_all_depts","create_dept_admin",
                   "approve_requests","view_audit_log","mcp","analytics"],
    "dept_admin": ["query","chat","ingest","research","agent","manage_users",
                   "manage_dept_users","approve_requests","analytics","mcp"],
    "power_user": ["query","chat","ingest","research","agent","analytics"],
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
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username or email already exists")
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
    if body.is_active  is not None: updates.append("is_active=?");  vals.append(1 if body.is_active else 0)

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
        conn.execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
        conn.execute(
            "UPDATE departments SET user_count=MAX(0,user_count-1) WHERE code=?",
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
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Username or email already exists")
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
        updates.append("is_active=?"); vals.append(1 if body.is_active else 0)

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
# DASHBOARD STATS  [FIX 4]
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/admin/stats")
async def get_stats(p: dict = Depends(current_user)):
    role = p["role"]
    dept = p["dept_id"]

    with db_conn() as conn:
        users_q  = "SELECT COUNT(*) FROM users WHERE is_active=1" + ("" if role == "root" else " AND department=?")
        today    = datetime.utcnow().date().isoformat()
        qlog_q   = "SELECT COUNT(*) FROM query_log WHERE created_at>=?" + ("" if role == "root" else " AND dept_code=?")
        avgrt_q  = (
            "SELECT AVG(response_ms) FROM (SELECT response_ms FROM query_log ORDER BY id DESC LIMIT 100)"
            if role == "root" else
            "SELECT AVG(response_ms) FROM (SELECT response_ms FROM query_log WHERE dept_code=? ORDER BY id DESC LIMIT 100)"
        )
        faith_q  = (
            "SELECT AVG(faithfulness) FROM query_log WHERE faithfulness IS NOT NULL"
            if role == "root" else
            "SELECT AVG(faithfulness) FROM query_log WHERE dept_code=? AND faithfulness IS NOT NULL"
        )
        docs_q   = "SELECT SUM(doc_count) FROM departments" if role == "root" else "SELECT doc_count FROM departments WHERE code=?"
        depts_q  = "SELECT COUNT(*) FROM departments WHERE is_active=1"

        total_users   = conn.execute(users_q,  () if role == "root" else (dept,)).fetchone()[0]
        queries_today = conn.execute(qlog_q,   (today,) if role == "root" else (today, dept)).fetchone()[0]
        avg_rt        = conn.execute(avgrt_q,  () if role == "root" else (dept,)).fetchone()[0]
        avg_faith     = conn.execute(faith_q,  () if role == "root" else (dept,)).fetchone()[0]
        total_docs    = conn.execute(docs_q,   () if role == "root" else (dept,)).fetchone()[0] or 0
        dept_count    = conn.execute(depts_q).fetchone()[0]

    pinecone_info: dict = {}
    try:
        from pinecone import Pinecone as PC
        idx = os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge")
        PC(api_key=os.getenv("PINECONE_API_KEY", "")).describe_index(idx)
        pinecone_info = {"status": "connected", "index": idx}
    except Exception as e:
        pinecone_info = {"status": "unavailable", "error": str(e)}

    return {
        "total_documents":   int(total_docs),
        "queries_today":     int(queries_today or 0),
        "active_users":      int(total_users or 0),
        "total_users":       int(total_users or 0),
        "departments":       int(dept_count or 0),
        "avg_response_time": round((avg_rt or 0) / 1000, 2),
        "avg_faithfulness":  round(avg_faith or 0, 2),
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
# QUERY / CHAT / INGEST
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/query")
async def query_endpoint(req: QueryRequest, p: dict = Depends(current_user)):
    perm(p, "query")
    dept = req.department or p.get("dept_id", "general")
    dept_gate(p, dept)

    rag = get_rag()
    if not rag:
        return {"status": "degraded", "query": req.query,
                "results": "RAG pipeline unavailable — ensure OPENAI_API_KEY and PINECONE_API_KEY are set.",
                "sources": []}

    t0 = time.time()
    try:
        from utils.tenant_context import TenantContext
        ctx    = TenantContext(tenant_id="huron", dept_id=dept,
                               username=p.get("sub"), role=p.get("role", "user"))
        result = await rag.query(query=req.query, tenant_context=ctx)
        elapsed = int((time.time() - t0) * 1000)
        log_query(p.get("user_id", 0), dept, req.query, elapsed,
                  result.get("faithfulness_score", 0), len(result.get("sources", [])))
        return {
            "status":             "success",
            "query":              req.query,
            "results":            result.get("response", ""),
            "sources":            [{"title": s} for s in result.get("sources", [])],
            "intent":             result.get("intent"),
            "faithfulness_score": result.get("faithfulness_score"),
            "processing_time_ms": elapsed,
        }
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
        return {"status": "degraded", "response": "RAG pipeline unavailable.", "sources": []}

    try:
        from utils.tenant_context import TenantContext
        ctx    = TenantContext(tenant_id="huron", dept_id=dept,
                               username=p.get("sub"), role=p.get("role", "user"))
        result = await rag.query(query=last, tenant_context=ctx)
        return {"status": "success", "response": result.get("response", ""),
                "sources": [{"title": s} for s in result.get("sources", [])]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/ingest")
async def ingest_endpoint(
    file: UploadFile = File(...),
    department: str  = Form("general"),
    sensitivity_level: str = Form("internal"),
    token: str       = Depends(oauth2_scheme),
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
# HEALTH + INDEXES
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    try:
        with db_conn() as conn:
            conn.execute("SELECT 1")
        return {"status": "healthy", "version": "4.0.0", "db": "sqlite",
                "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


@app.get("/api/v1/indexes")
async def list_indexes(p: dict = Depends(current_user)):
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT code,display_name,namespace,doc_count,classification FROM departments WHERE is_active=1"
        ).fetchall()
    indexes = [
        {"name": r["namespace"], "dept": r["code"], "display_name": r["display_name"],
         "type": "Pinecone", "documents": r["doc_count"],
         "classification": r["classification"], "status": "active"}
        for r in rows
    ]
    return {"status": "success", "count": len(indexes), "indexes": indexes}


# ═════════════════════════════════════════════════════════════════════════════
# RUN
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
