"""
VaultMind GenAI Knowledge Assistant - Authentication Middleware
Production-ready middleware for FastAPI request authentication and authorization
Refactored to remove Streamlit dependencies - uses JWT Bearer tokens
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, Dict, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..auth.authentication import auth_manager, UserRole

logger = logging.getLogger(__name__)

# OAuth2 scheme for Bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class UserContext:
    """User context extracted from JWT token"""
    def __init__(self, user_data: Dict[str, Any]):
        self.username = user_data.get('username', '')
        self.email = user_data.get('email', '')
        self.role = user_data.get('role', 'viewer')
        self.department = user_data.get('department', '')
        self.permissions = user_data.get('permissions', [])
        self.authenticated = True
    
    def has_role(self, required_role: str) -> bool:
        """Check if user has required role or higher"""
        role_hierarchy = {'viewer': 0, 'user': 1, 'power_user': 2, 'admin': 3}
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        return user_level >= required_level


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[UserContext]:
    """
    FastAPI dependency to get current authenticated user from JWT token.
    Returns None if not authenticated (for optional auth endpoints).
    """
    if not token:
        return None
    
    try:
        payload = auth_manager.verify_token(token)
        if not payload:
            return None
        return UserContext(payload)
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None


async def require_auth(token: str = Depends(oauth2_scheme)) -> UserContext:
    """
    FastAPI dependency to require authentication.
    Raises HTTPException if not authenticated.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = auth_manager.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return UserContext(payload)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_role: str):
    """
    FastAPI dependency factory for role-based access control.
    Usage: @app.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    async def role_checker(user: UserContext = Depends(require_auth)) -> UserContext:
        if not user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return user
    return role_checker


def require_admin():
    """Dependency to require admin role"""
    return require_role("admin")


def require_user():
    """Dependency to require user role or higher"""
    return require_role("user")


class AuthMiddleware:
    """Authentication utilities for FastAPI"""
    
    @staticmethod
    def log_user_action(user: UserContext, action: str, details: str = ""):
        """Log user actions for audit trail"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] User: {user.username} | Role: {user.role} | Action: {action} | Details: {details}")
    
    @staticmethod
    def get_user_permissions(user: Optional[UserContext]) -> dict:
        """Get user's permissions based on role"""
        if not user or not user.authenticated:
            return {
                'can_upload': False,
                'can_query': False,
                'can_chat': False,
                'can_use_agents': False,
                'can_manage_users': False,
                'can_view_mcp': False,
                'can_manage_content': False
            }
        
        if user.role == 'admin':
            return {
                'can_upload': True,
                'can_query': True,
                'can_chat': True,
                'can_use_agents': True,
                'can_manage_users': True,
                'can_view_mcp': True,
                'can_manage_content': True
            }
        elif user.role in ('user', 'power_user'):
            return {
                'can_upload': True,
                'can_query': True,
                'can_chat': True,
                'can_use_agents': True,
                'can_manage_users': False,
                'can_view_mcp': False,
                'can_manage_content': False
            }
        else:  # viewer
            return {
                'can_upload': True,
                'can_query': True,
                'can_chat': True,
                'can_use_agents': True,
                'can_manage_users': False,
                'can_view_mcp': True,
                'can_manage_content': False
            }


# Global middleware instance
auth_middleware = AuthMiddleware()
