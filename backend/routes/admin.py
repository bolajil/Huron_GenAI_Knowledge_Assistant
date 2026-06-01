"""
Admin routes: user management, department management (root-only).
"""

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, status

import bcrypt

from core.database import db_conn, get_user_by_id, write_audit
from core.security import require_root, require_admin, current_user
from models.schemas import CreateUserRequest, UpdateUserRequest

router = APIRouter(prefix="/api/v1", tags=["admin"])


# ═══════════════════════════════════════════════════════════════════════════════
# ROOT-ONLY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/root/users")
async def root_list_users(p: dict = Depends(require_root)):
    """List all users (root only)."""
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT u.id,u.username,u.email,u.full_name,u.role,u.department,"
            "u.is_active,u.last_login,u.created_at,c.username as created_by_name "
            "FROM users u LEFT JOIN users c ON u.created_by=c.id ORDER BY u.created_at DESC"
        ).fetchall()
    return {"users": [dict(r) for r in rows]}


@router.post("/root/users")
async def root_create_user(body: CreateUserRequest, p: dict = Depends(require_root)):
    """Create a new user (root only)."""
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


@router.put("/root/users/{user_id}")
@router.patch("/root/users/{user_id}")
async def root_update_user(user_id: int, body: UpdateUserRequest, p: dict = Depends(require_root)):
    """Update a user (root only)."""
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "root":
        raise HTTPException(status_code=400, detail="Cannot modify root user")

    updates, vals = [], []
    if body.full_name is not None:
        updates.append("full_name=?")
        vals.append(body.full_name)
    if body.role is not None:
        updates.append("role=?")
        vals.append(body.role)
    if body.department is not None:
        updates.append("department=?")
        vals.append(body.department)
    if body.is_active is not None:
        updates.append("is_active=?")
        vals.append(bool(body.is_active))

    if updates:
        vals.append(user_id)
        with db_conn() as conn:
            conn.execute(
                f"UPDATE users SET {','.join(updates)},updated_at=CURRENT_TIMESTAMP WHERE id=?",
                vals
            )
            conn.commit()
    
    write_audit(p["user_id"], p["sub"], "update_user", detail=f"Updated {target['username']}")
    return {"status": "success"}


@router.delete("/root/users/{user_id}")
async def root_delete_user(user_id: int, p: dict = Depends(require_root)):
    """Deactivate a user (root only)."""
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


@router.get("/root/departments")
async def root_list_departments(p: dict = Depends(require_root)):
    """List all departments (root only)."""
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT d.*,u.username as admin_username FROM departments d "
            "LEFT JOIN users u ON d.admin_user_id=u.id"
        ).fetchall()
    return {"departments": [dict(r) for r in rows]}


@router.post("/root/departments/{code}/assign-admin")
async def assign_dept_admin(code: str, body: dict, p: dict = Depends(require_root)):
    """Assign a department admin (root only)."""
    user = get_user_by_id(body.get("user_id"))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    with db_conn() as conn:
        conn.execute("UPDATE departments SET admin_user_id=? WHERE code=?", (user["id"], code))
        conn.execute("UPDATE users SET role='dept_admin',department=? WHERE id=?", (code, user["id"]))
        conn.commit()
    
    write_audit(p["user_id"], p["sub"], "assign_dept_admin", code,
                detail=f"Assigned {user['username']} as admin")
    return {"status": "success"}


# ═══════════════════════════════════════════════════════════════════════════════
# DEPT-ADMIN ENDPOINTS (alias for frontend compatibility)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dept-admin/users")
async def dept_admin_list_users(p: dict = Depends(require_admin)):
    """List users in admin's department."""
    dept = p.get("dept_id", "")
    if p.get("role") == "root":
        return await root_list_users(p)
    
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT id,username,email,full_name,role,department,is_active,last_login,created_at "
            "FROM users WHERE department=? ORDER BY created_at DESC",
            (dept,)
        ).fetchall()
    return {"users": [dict(r) for r in rows]}


@router.post("/dept-admin/users")
async def dept_admin_create_user(body: CreateUserRequest, p: dict = Depends(require_admin)):
    """Create user in admin's department."""
    if p.get("role") == "root":
        return await root_create_user(body, p)
    
    if body.department != p.get("dept_id"):
        raise HTTPException(status_code=403, detail="Can only create users in your department")
    if body.role in ("root", "dept_admin"):
        raise HTTPException(status_code=403, detail="Cannot create admin users")
    
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
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Username or email already exists")
        raise
    
    write_audit(p["user_id"], p["sub"], "create_user", body.department,
                detail=f"Created {body.role} {body.username}")
    return {"status": "success", "message": f"User {body.username} created"}
