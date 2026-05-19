"""
Huron GenAI Knowledge Assistant - Database Models
SQLAlchemy models for production PostgreSQL deployment

Tables:
- users: User accounts with multi-tenant support
- user_sessions: Active sessions for token management
- departments: Department configuration and namespaces
- audit_logs: Compliance audit trail (SOC 2, HIPAA)
- user_departments: Many-to-many user-department mapping

Author: Production Scalability Team
Date: May 2026
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey,
    Enum as SQLEnum, Index, Table, JSON
)
from sqlalchemy.orm import relationship
from enum import Enum

from app.auth.database import Base


class UserRole(str, Enum):
    """User role levels."""
    ADMIN = "admin"
    POWER_USER = "power_user"
    USER = "user"
    VIEWER = "viewer"


class ClearanceLevel(str, Enum):
    """Document sensitivity clearance levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    HIPAA_PHI = "hipaa_phi"


class AuditAction(str, Enum):
    """Audit log action types."""
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    QUERY = "query"
    INGEST = "ingest"
    DELETE = "delete"
    ADMIN_ACTION = "admin_action"
    PERMISSION_CHANGE = "permission_change"
    NAMESPACE_ACCESS = "namespace_access"
    CROSS_NAMESPACE_ATTEMPT = "cross_namespace_attempt"


# Many-to-many relationship table for user departments
user_departments = Table(
    'user_departments',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('department_id', Integer, ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True),
    Column('granted_at', DateTime, default=datetime.utcnow),
    Column('granted_by', String(100)),
)


class User(Base):
    """User account model with multi-tenant support."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Role and permissions
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    clearance_level = Column(SQLEnum(ClearanceLevel), default=ClearanceLevel.INTERNAL, nullable=False)
    
    # Multi-tenant fields
    tenant_id = Column(String(50), default='huron', nullable=False, index=True)
    primary_dept_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)  # Encrypted TOTP secret
    
    # Security tracking
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # SSO fields
    sso_provider = Column(String(50), nullable=True)  # 'okta', 'azure_ad', None for local
    sso_subject_id = Column(String(255), nullable=True)  # External user ID from SSO
    
    # Relationships
    primary_department = relationship("Department", foreign_keys=[primary_dept_id], back_populates="primary_users")
    departments = relationship("Department", secondary=user_departments, back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes for performance at scale
    __table_args__ = (
        Index('ix_users_tenant_dept', 'tenant_id', 'primary_dept_id'),
        Index('ix_users_sso', 'sso_provider', 'sso_subject_id'),
        Index('ix_users_active', 'is_active', 'tenant_id'),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JWT claims."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role.value,
            'clearance_level': self.clearance_level.value,
            'tenant_id': self.tenant_id,
            'dept_id': self.primary_dept_id,
            'dept_ids': [d.id for d in self.departments],
            'is_mfa_enabled': self.is_mfa_enabled,
        }


class UserSession(Base):
    """Active user sessions for token management."""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Token management
    session_token = Column(String(500), unique=True, nullable=False, index=True)
    refresh_token = Column(String(500), unique=True, nullable=True, index=True)
    
    # Session context
    dept_id = Column(Integer, ForeignKey('departments.id'), nullable=True)  # Active department for this session
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    department = relationship("Department")
    
    __table_args__ = (
        Index('ix_sessions_user_active', 'user_id', 'is_active'),
        Index('ix_sessions_expires', 'expires_at'),
    )


class Department(Base):
    """Department configuration for namespace isolation."""
    __tablename__ = 'departments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Department identity
    code = Column(String(50), unique=True, nullable=False, index=True)  # 'hr', 'finance', 'legal'
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Namespace configuration
    namespace = Column(String(100), unique=True, nullable=False)  # 'vaultmind-huron-hr-general'
    sensitivity_level = Column(SQLEnum(ClearanceLevel), default=ClearanceLevel.INTERNAL)
    
    # Configuration (stored as JSON)
    attention_profile = Column(JSON, nullable=True)  # RAG attention weights
    crawler_config = Column(JSON, nullable=True)  # Web crawler settings
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_pilot = Column(Boolean, default=False)  # True during pilot phase
    go_live_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    primary_users = relationship("User", foreign_keys="User.primary_dept_id", back_populates="primary_department")
    users = relationship("User", secondary=user_departments, back_populates="departments")
    
    __table_args__ = (
        Index('ix_departments_active', 'is_active', 'code'),
    )


class AuditLog(Base):
    """Compliance audit trail for SOC 2 and HIPAA."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Who
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    username = Column(String(100), nullable=False)  # Denormalized for log retention
    
    # What
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)  # 'document', 'query', 'user'
    resource_id = Column(String(255), nullable=True)
    
    # Context
    tenant_id = Column(String(50), nullable=False, index=True)
    dept_id = Column(Integer, ForeignKey('departments.id', ondelete='SET NULL'), nullable=True)
    namespace = Column(String(100), nullable=True)
    
    # Details
    details = Column(JSON, nullable=True)  # Action-specific details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Result
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamp (immutable)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    department = relationship("Department")
    
    __table_args__ = (
        Index('ix_audit_user_action', 'user_id', 'action', 'created_at'),
        Index('ix_audit_tenant_time', 'tenant_id', 'created_at'),
        Index('ix_audit_dept_time', 'dept_id', 'created_at'),
        Index('ix_audit_namespace', 'namespace', 'created_at'),
    )
