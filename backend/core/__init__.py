"""Core module - configuration, database, and security utilities."""

from .config import settings, APP_ENV, SECRET_KEY, ALGORITHM, TOKEN_HOURS
from .database import db_conn, get_user_by_id, get_user_by_login, write_audit, init_db
from .security import (
    create_token,
    verify_token,
    blacklist_token,
    current_user,
    require_root,
    require_admin,
    ROLE_PERMISSIONS,
)

__all__ = [
    "settings",
    "APP_ENV",
    "SECRET_KEY",
    "ALGORITHM",
    "TOKEN_HOURS",
    "db_conn",
    "get_user_by_id",
    "get_user_by_login",
    "write_audit",
    "init_db",
    "create_token",
    "verify_token",
    "blacklist_token",
    "current_user",
    "require_root",
    "require_admin",
    "ROLE_PERMISSIONS",
]
