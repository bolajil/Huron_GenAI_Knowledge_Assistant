"""
Huron GenAI Knowledge Assistant - Authentication Middleware
Production-ready middleware for FastAPI request authentication and authorization

Features:
- JWT Bearer token authentication
- Multi-tenant context injection via TenantContext
- Role-based access control (RBAC)
- Department-scoped namespace isolation
- Audit logging integration

Author: Production Scalability Team
Date: May 2026
"""

import logging
import time
import uuid
from functools import wraps
from typing import Callable, Any, Dict, Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from ..auth.authentication import auth_manager, UserRole
from utils.tenant_context import (
    TenantContext, 
    set_current_context, 
    get_current_context,
    clear_context,
    ClearanceLevel
)

logger = logging.getLogger(__name__)

# OAuth2 scheme for Bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class UserContext:
    """
    User context extracted from JWT token with multi-tenant support.
    
    Now integrates with TenantContext for namespace isolation.
    """
    def __init__(self, user_data: Dict[str, Any], request: Optional[Request] = None):
        self.username = user_data.get('username', '')
        self.email = user_data.get('email', '')
        self.role = user_data.get('role', 'viewer')
        self.department = user_data.get('dept_id', '')  # Primary department
        self.departments = user_data.get('dept_ids', [])  # All accessible departments
        self.tenant_id = user_data.get('tenant_id', 'huron')
        self.clearance_level = user_data.get('clearance_level', 'internal')
        self.permissions = user_data.get('permissions', [])
        self.authenticated = True
        
        # Create TenantContext from JWT claims
        self._tenant_context = TenantContext.from_jwt_claims(user_data)
        
        # Add request metadata
        if request:
            self._tenant_context.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
            self._tenant_context.ip_address = request.client.host if request.client else None
        
        # Set as current context for this request
        set_current_context(self._tenant_context)
    
    @property
    def tenant_context(self) -> TenantContext:
        """Get the TenantContext for this user"""
        return self._tenant_context
    
    def get_namespace(self, doc_type: str = "general") -> str:
        """Get the Pinecone namespace for this user's primary department"""
        return self._tenant_context.get_namespace(doc_type)
    
    def can_access_department(self, dept_id: str) -> bool:
        """Check if user can access a specific department"""
        return self._tenant_context.can_access_department(dept_id)
    
    def has_role(self, required_role: str) -> bool:
        """Check if user has required role or higher"""
        role_hierarchy = {'viewer': 0, 'user': 1, 'power_user': 2, 'admin': 3}
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        return user_level >= required_level
    
    def has_clearance(self, required_level: str) -> bool:
        """Check if user has sufficient clearance level"""
        try:
            required = ClearanceLevel.from_string(required_level)
            return self._tenant_context.can_access_clearance(required)
        except:
            return False


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[UserContext]:
    """
    FastAPI dependency to get current authenticated user from JWT token.
    Returns None if not authenticated (for optional auth endpoints).
    
    Automatically sets TenantContext for namespace isolation.
    """
    if not token:
        return None
    
    try:
        payload = auth_manager.verify_token(token)
        if not payload:
            return None
        return UserContext(payload, request)
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None


async def require_auth(
    request: Request,
    token: str = Depends(oauth2_scheme)
) -> UserContext:
    """
    FastAPI dependency to require authentication.
    Raises HTTPException if not authenticated.
    
    Sets TenantContext for namespace isolation on successful auth.
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
        
        # Validate dept_id is present (required for namespace isolation)
        if not payload.get('dept_id'):
            logger.warning(f"JWT missing dept_id for user {payload.get('username')}")
            # Don't fail - allow access but log warning
        
        return UserContext(payload, request)
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


def require_department(dept_id: str):
    """
    FastAPI dependency factory for department-scoped access control.
    
    Usage: @app.get("/legal/docs", dependencies=[Depends(require_department("legal"))])
    
    Raises 403 if user doesn't have access to the specified department.
    """
    async def department_checker(user: UserContext = Depends(require_auth)) -> UserContext:
        if not user.can_access_department(dept_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to department '{dept_id}' denied"
            )
        return user
    return department_checker


def require_clearance(level: str):
    """
    FastAPI dependency factory for clearance-level access control.
    
    Usage: @app.get("/restricted", dependencies=[Depends(require_clearance("confidential"))])
    
    Raises 403 if user doesn't have sufficient clearance.
    """
    async def clearance_checker(user: UserContext = Depends(require_auth)) -> UserContext:
        if not user.has_clearance(level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Clearance level '{level}' required"
            )
        return user
    return clearance_checker


def get_tenant_context(user: UserContext = Depends(require_auth)) -> TenantContext:
    """
    FastAPI dependency to get the current TenantContext.
    
    Usage:
        @app.get("/query")
        async def query(ctx: TenantContext = Depends(get_tenant_context)):
            namespace = ctx.get_namespace()
            ...
    """
    return user.tenant_context


async def cleanup_context():
    """
    Cleanup TenantContext after request.
    Use as a background task or in middleware.
    """
    clear_context()


# Global middleware instance
auth_middleware = AuthMiddleware()


# Export for easy imports
__all__ = [
    'UserContext',
    'get_current_user',
    'require_auth',
    'require_role',
    'require_admin',
    'require_user',
    'require_department',
    'require_clearance',
    'get_tenant_context',
    'cleanup_context',
    'auth_middleware',
    'oauth2_scheme',
]
