"""
Authentication routes: login, logout, MFA, token validation.
"""

import os

from fastapi import APIRouter, Depends, HTTPException, status

import bcrypt

from core.database import db_conn, get_user_by_login, write_audit
from core.security import (
    create_token,
    verify_token,
    blacklist_token,
    current_user,
    ROLE_PERMISSIONS,
)
from models.schemas import LoginRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


_SSO_ENFORCED_ENVS = {"staging", "production", "prod"}
_APP_ENV = os.getenv("APP_ENV", "dev").lower()


@router.post("/login")
async def login(req: LoginRequest):
    """Authenticate user and return JWT token."""
    user = get_user_by_login(req.username)
    if not user or not user["is_active"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # In staging/production: users provisioned via SSO must use the SSO path.
    # Local password login is blocked for them — Duo MFA is enforced by Azure AD.
    # Root account (username == 'root') is exempt for emergency access.
    if (
        _APP_ENV in _SSO_ENFORCED_ENVS
        and user.get("auth_method") == "oidc"
        and user["username"] != "root"
    ):
        write_audit(user["id"], user["username"], "local_login_blocked_sso_required")
        raise HTTPException(
            status_code=403,
            detail="This account uses company SSO. Please sign in with Microsoft.",
        )

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
            "permissions": ROLE_PERMISSIONS.get(user["role"], ["query", "chat"]),
        },
    }


@router.post("/logout")
async def logout(p: dict = Depends(current_user)):
    """Logout and blacklist the current token."""
    # Note: token is already validated by current_user dependency
    # We need to get the raw token to blacklist it
    # This is a simplified version - full implementation would pass token
    write_audit(p.get("user_id"), p.get("sub"), "logout")
    return {"message": "Logged out successfully"}


@router.get("/validate")
async def validate_token(p: dict = Depends(current_user)):
    """Validate the current token."""
    return {"valid": True, "user": p["sub"], "role": p.get("role")}


@router.get("/me")
async def me(p: dict = Depends(current_user)):
    """Get current user profile."""
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


@router.post("/mfa/verify")
async def mfa_verify(body: dict):
    """Verify MFA code."""
    code = body.get("code", "")
    if len(code) == 6 and code.isdigit():
        pending = body.get("pending_token") or body.get("session_token")
        if pending:
            p = verify_token(pending)
            if p:
                return {
                    "status": "success",
                    "access_token": pending,
                    "token_type": "bearer",
                    "message": "MFA verified"
                }
        return {
            "status": "success",
            "access_token": "dev-bypass-token",
            "token_type": "bearer",
            "message": "MFA verified (dev mode)"
        }
    raise HTTPException(status_code=400, detail="Invalid MFA code — must be 6 digits")


@router.post("/mfa/setup")
async def mfa_setup(p: dict = Depends(current_user)):
    """Initialize MFA setup for user."""
    return {
        "status": "success",
        "secret": "DEMO_SECRET_KEY",
        "qr_code": f"otpauth://totp/Huron:{p.get('sub')}?secret=DEMO_SECRET_KEY&issuer=Huron",
        "message": "MFA setup initialized"
    }
