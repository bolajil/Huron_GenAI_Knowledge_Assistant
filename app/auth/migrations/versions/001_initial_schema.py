"""Initial schema for production deployment

Revision ID: 001_initial
Revises: 
Create Date: 2026-05-19

Creates tables:
- users: User accounts with multi-tenant support
- user_sessions: Token management
- departments: Namespace configuration
- audit_logs: Compliance audit trail
- user_departments: Many-to-many mapping
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create departments table first (referenced by users)
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('namespace', sa.String(length=100), nullable=False),
        sa.Column('sensitivity_level', sa.Enum('public', 'internal', 'confidential', 'restricted', 'hipaa_phi', name='clearancelevel'), nullable=True),
        sa.Column('attention_profile', sa.JSON(), nullable=True),
        sa.Column('crawler_config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_pilot', sa.Boolean(), nullable=False, default=False),
        sa.Column('go_live_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        sa.UniqueConstraint('namespace')
    )
    op.create_index('ix_departments_active', 'departments', ['is_active', 'code'])
    op.create_index('ix_departments_code', 'departments', ['code'])
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'power_user', 'user', 'viewer', name='userrole'), nullable=False, default='user'),
        sa.Column('clearance_level', sa.Enum('public', 'internal', 'confidential', 'restricted', 'hipaa_phi', name='clearancelevel'), nullable=False, default='internal'),
        sa.Column('tenant_id', sa.String(length=50), nullable=False, default='huron'),
        sa.Column('primary_dept_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_mfa_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('mfa_secret', sa.String(length=255), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('sso_provider', sa.String(length=50), nullable=True),
        sa.Column('sso_subject_id', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['primary_dept_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_tenant_dept', 'users', ['tenant_id', 'primary_dept_id'])
    op.create_index('ix_users_sso', 'users', ['sso_provider', 'sso_subject_id'])
    op.create_index('ix_users_active', 'users', ['is_active', 'tenant_id'])
    
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(length=500), nullable=False),
        sa.Column('refresh_token', sa.String(length=500), nullable=True),
        sa.Column('dept_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_reason', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dept_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token'),
        sa.UniqueConstraint('refresh_token')
    )
    op.create_index('ix_sessions_token', 'user_sessions', ['session_token'])
    op.create_index('ix_sessions_refresh', 'user_sessions', ['refresh_token'])
    op.create_index('ix_sessions_user_active', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('ix_sessions_expires', 'user_sessions', ['expires_at'])
    
    # Create user_departments many-to-many table
    op.create_table(
        'user_departments',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('granted_by', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'department_id')
    )
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('action', sa.Enum('login', 'logout', 'login_failed', 'query', 'ingest', 'delete', 'admin_action', 'permission_change', 'namespace_access', 'cross_namespace_attempt', name='auditaction'), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('tenant_id', sa.String(length=50), nullable=False),
        sa.Column('dept_id', sa.Integer(), nullable=True),
        sa.Column('namespace', sa.String(length=100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['dept_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_created', 'audit_logs', ['created_at'])
    op.create_index('ix_audit_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_user_action', 'audit_logs', ['user_id', 'action', 'created_at'])
    op.create_index('ix_audit_tenant_time', 'audit_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_dept_time', 'audit_logs', ['dept_id', 'created_at'])
    op.create_index('ix_audit_namespace', 'audit_logs', ['namespace', 'created_at'])
    
    # Insert default departments (8 as per scalability plan)
    op.execute("""
        INSERT INTO departments (code, name, namespace, sensitivity_level, is_active, is_pilot)
        VALUES 
            ('hr', 'Human Resources', 'vaultmind-huron-hr-general', 'internal', true, true),
            ('finance', 'Finance', 'vaultmind-huron-finance-general', 'confidential', true, false),
            ('legal', 'Legal', 'vaultmind-huron-legal-general', 'restricted', true, false),
            ('operations', 'Operations', 'vaultmind-huron-operations-general', 'internal', true, false),
            ('it', 'Information Technology', 'vaultmind-huron-it-general', 'confidential', true, false),
            ('marketing', 'Marketing', 'vaultmind-huron-marketing-general', 'internal', true, false),
            ('clinical', 'Clinical', 'vaultmind-huron-clinical-general', 'hipaa_phi', false, false),
            ('external', 'External Research', 'vaultmind-huron-external-general', 'public', true, false)
    """)


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('user_departments')
    op.drop_table('user_sessions')
    op.drop_table('users')
    op.drop_table('departments')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS auditaction")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS clearancelevel")
