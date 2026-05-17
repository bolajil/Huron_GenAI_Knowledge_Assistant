"""
Tenant Context Manager - Centralized Multi-Tenant Context

This module provides a unified way to manage tenant/department context
across all components of the VaultMind system.

Usage:
    from utils.tenant_context import TenantContext, get_current_context
    
    # From JWT token
    ctx = TenantContext.from_jwt_claims(token_payload)
    
    # Manual creation
    ctx = TenantContext(tenant_id="huron", dept_id="legal")
    
    # Get namespace for Pinecone
    namespace = ctx.get_namespace()
    
    # Check access
    if ctx.can_access_department("finance"):
        # Allow cross-dept query
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import re
import os

logger = logging.getLogger(__name__)


class ClearanceLevel(Enum):
    """Document sensitivity clearance levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    HIPAA_PHI = "hipaa_phi"
    
    @classmethod
    def from_string(cls, value: str) -> "ClearanceLevel":
        """Parse clearance level from string"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.INTERNAL


@dataclass
class TenantContext:
    """
    Centralized tenant/department context for multi-tenant isolation.
    
    This context should be created at the start of each request and
    passed through all layers (API → Service → Adapter).
    """
    
    # Required fields
    tenant_id: str
    
    # Optional fields with defaults
    dept_id: Optional[str] = None
    dept_ids: List[str] = field(default_factory=list)
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: str = "user"
    clearance_level: ClearanceLevel = ClearanceLevel.INTERNAL
    
    # Request metadata
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    
    def __post_init__(self):
        """Normalize fields after initialization"""
        # Ensure dept_ids includes primary dept_id
        if self.dept_id and self.dept_id not in self.dept_ids:
            self.dept_ids = [self.dept_id] + list(self.dept_ids)
        
        # Ensure clearance_level is enum
        if isinstance(self.clearance_level, str):
            self.clearance_level = ClearanceLevel.from_string(self.clearance_level)
    
    @classmethod
    def from_jwt_claims(cls, claims: Dict[str, Any]) -> "TenantContext":
        """
        Create TenantContext from JWT token claims.
        
        Expected claims:
        - tenant_id: str
        - dept_id: str (primary department)
        - dept_ids: List[str] (all accessible departments)
        - username: str
        - role: str
        - clearance_level: str
        """
        return cls(
            tenant_id=claims.get("tenant_id", "huron"),
            dept_id=claims.get("dept_id"),
            dept_ids=claims.get("dept_ids", []),
            username=claims.get("username"),
            role=claims.get("role", "user"),
            clearance_level=ClearanceLevel.from_string(
                claims.get("clearance_level", "internal")
            ),
        )
    
    @classmethod
    def from_request_headers(cls, headers: Dict[str, str]) -> "TenantContext":
        """
        Create TenantContext from HTTP headers.
        
        Expected headers:
        - X-Tenant-ID: str
        - X-Dept-ID: str
        - X-User-ID: str
        """
        return cls(
            tenant_id=headers.get("X-Tenant-ID", headers.get("x-tenant-id", "huron")),
            dept_id=headers.get("X-Dept-ID", headers.get("x-dept-id")),
            user_id=headers.get("X-User-ID", headers.get("x-user-id")),
        )
    
    @classmethod
    def default(cls) -> "TenantContext":
        """Create a default context for development/testing"""
        return cls(
            tenant_id=os.getenv("DEFAULT_TENANT", "huron"),
            dept_id=os.getenv("DEFAULT_DEPT", "general"),
            dept_ids=["general"],
            role="user",
            clearance_level=ClearanceLevel.INTERNAL,
        )
    
    def get_namespace(self, doc_type: str = "general") -> str:
        """
        Generate Pinecone namespace for this context.
        
        Format: vaultmind-{tenant}-{dept}-{type}
        Example: vaultmind-huron-legal-general
        
        Args:
            doc_type: Document type suffix (general, external, etc.)
        
        Returns:
            Sanitized namespace string (max 45 chars)
        """
        if not self.dept_id:
            raise ValueError("dept_id is required to generate namespace")
        
        name = f"vaultmind-{self.tenant_id}-{self.dept_id}-{doc_type}"
        # Sanitize: lowercase, replace invalid chars, truncate
        name = re.sub(r"[^a-z0-9-]", "-", name.lower())[:45]
        return name
    
    def get_all_namespaces(self, doc_type: str = "general") -> List[str]:
        """
        Get all namespaces this context can access.
        
        Useful for cross-department searches when user has multiple dept access.
        """
        namespaces = []
        for dept in self.dept_ids:
            name = f"vaultmind-{self.tenant_id}-{dept}-{doc_type}"
            name = re.sub(r"[^a-z0-9-]", "-", name.lower())[:45]
            namespaces.append(name)
        return namespaces
    
    def can_access_department(self, dept_id: str) -> bool:
        """Check if this context has access to a department"""
        # Admins can access all departments
        if self.role == "admin":
            return True
        return dept_id in self.dept_ids
    
    def can_access_clearance(self, required_level: ClearanceLevel) -> bool:
        """Check if context has sufficient clearance"""
        level_order = [
            ClearanceLevel.PUBLIC,
            ClearanceLevel.INTERNAL,
            ClearanceLevel.CONFIDENTIAL,
            ClearanceLevel.RESTRICTED,
            ClearanceLevel.HIPAA_PHI,
        ]
        
        user_level = level_order.index(self.clearance_level)
        required = level_order.index(required_level)
        
        return user_level >= required
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate that context has required fields.
        
        Returns:
            (is_valid, error_message)
        """
        if not self.tenant_id:
            return False, "tenant_id is required"
        if not self.dept_id:
            return False, "dept_id is required for namespace isolation"
        return True, ""
    
    def to_metadata(self) -> Dict[str, Any]:
        """
        Convert context to metadata dict for document tagging.
        
        This metadata is stored with each document in the vector store.
        """
        return {
            "tenant_id": self.tenant_id,
            "dept_id": self.dept_id,
            "uploaded_by": self.username or "system",
            "clearance_level": self.clearance_level.value,
            "namespace": self.get_namespace() if self.dept_id else None,
        }
    
    def to_audit_log(self) -> Dict[str, Any]:
        """Convert context to audit log entry"""
        return {
            "tenant_id": self.tenant_id,
            "dept_id": self.dept_id,
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "clearance_level": self.clearance_level.value,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
        }
    
    def __str__(self) -> str:
        return f"TenantContext(tenant={self.tenant_id}, dept={self.dept_id}, user={self.username})"


# Thread-local storage for current context
import threading
_context_storage = threading.local()


def set_current_context(ctx: TenantContext) -> None:
    """Set the current tenant context for this thread/request"""
    _context_storage.context = ctx


def get_current_context() -> Optional[TenantContext]:
    """Get the current tenant context for this thread/request"""
    return getattr(_context_storage, "context", None)


def require_context() -> TenantContext:
    """
    Get current context or raise if not set.
    
    Use this in functions that require tenant context.
    """
    ctx = get_current_context()
    if ctx is None:
        raise RuntimeError("Tenant context not set. Ensure middleware is configured.")
    return ctx


def clear_context() -> None:
    """Clear the current tenant context"""
    if hasattr(_context_storage, "context"):
        delattr(_context_storage, "context")


# Context manager for scoped context
from contextlib import contextmanager

@contextmanager
def tenant_scope(ctx: TenantContext):
    """
    Context manager for temporary tenant context.
    
    Usage:
        with tenant_scope(TenantContext(tenant_id="huron", dept_id="legal")):
            # All operations in this block use the specified context
            results = search_documents(query)
    """
    previous = get_current_context()
    try:
        set_current_context(ctx)
        yield ctx
    finally:
        if previous:
            set_current_context(previous)
        else:
            clear_context()
