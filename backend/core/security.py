"""
Security utilities: JWT tokens, authentication, authorization.
"""

from __future__ import annotations

import os
import json
import hashlib
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .config import SECRET_KEY, ALGORITHM, TOKEN_HOURS, MCP_ENCRYPTION_KEY, REDIS_URL

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ─── Role Permissions ────────────────────────────────────────────────────────
ROLE_PERMISSIONS = {
    "root": ["query", "chat", "ingest", "agent", "admin", "analytics", "indexes", "research"],
    "dept_admin": ["query", "chat", "ingest", "agent", "analytics", "admin_dept"],
    "power_user": ["query", "chat", "ingest", "agent", "analytics", "research"],
    "user": ["query", "chat", "ingest"],
    "viewer": ["query"],
}

CLEARANCE_LEVELS = {"root": 5, "dept_admin": 4, "power_user": 3, "user": 2, "viewer": 1}

# ─── Token Blacklist ─────────────────────────────────────────────────────────
_token_blacklist: set[str] = set()
_redis_client = None

if REDIS_URL:
    try:
        import redis as _redis_lib
        _redis_client = _redis_lib.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        logger.info("Redis JWT blacklist active")
    except Exception as e:
        logger.warning("Redis unavailable (%s) — falling back to in-memory blacklist", e)
        _redis_client = None


def blacklist_token(token: str):
    """Add a token to the blacklist."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti", "")
        exp = payload.get("exp", 0)
        ttl = max(0, exp - int(datetime.utcnow().timestamp()))
        
        if _redis_client:
            _redis_client.setex(f"blacklist:{jti}", ttl, "1")
        else:
            _token_blacklist.add(jti)
    except jwt.PyJWTError:
        pass


def is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI is blacklisted."""
    if _redis_client:
        return _redis_client.exists(f"blacklist:{jti}") > 0
    return jti in _token_blacklist


def create_token(user: dict) -> str:
    """Create a JWT token for a user."""
    import secrets
    
    now = datetime.utcnow()
    payload = {
        "sub": user["username"],
        "user_id": user["id"],
        "email": user.get("email", ""),
        "full_name": user.get("full_name", ""),
        "role": user["role"],
        "dept_id": user["department"],
        "permissions": ROLE_PERMISSIONS.get(user["role"], ["query"]),
        "clearance_level": CLEARANCE_LEVELS.get(user["role"], 1),
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_HOURS),
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti", "")
        if is_token_blacklisted(jti):
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


async def current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to get the current authenticated user."""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def require_root(p: dict = Depends(current_user)) -> dict:
    """Dependency to require root role."""
    if p.get("role") != "root":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Root access required")
    return p


async def require_admin(p: dict = Depends(current_user)) -> dict:
    """Dependency to require admin (root or dept_admin) role."""
    if p.get("role") not in ("root", "dept_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return p


# ─── MCP Encryption ──────────────────────────────────────────────────────────
from cryptography.fernet import Fernet as _Fernet


def _fernet() -> _Fernet:
    """Get Fernet instance for MCP credential encryption."""
    if MCP_ENCRYPTION_KEY:
        raw = hashlib.sha256(MCP_ENCRYPTION_KEY.encode()).digest()
    else:
        raw = hashlib.sha256(SECRET_KEY.encode()).digest()
    return _Fernet(base64.urlsafe_b64encode(raw))


def encrypt_config(cfg: dict) -> str:
    """Encrypt a configuration dict."""
    return _fernet().encrypt(json.dumps(cfg).encode()).decode()


def decrypt_config(ciphertext: str) -> dict:
    """Decrypt a configuration dict."""
    return json.loads(_fernet().decrypt(ciphertext.encode()))
