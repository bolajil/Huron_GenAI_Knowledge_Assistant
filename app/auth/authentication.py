"""
VaultMind GenAI Knowledge Assistant - Authentication System
Production-ready user authentication with role-based access control
"""

import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sqlite3
from pathlib import Path
import os
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class UserRole(Enum):
    ADMIN = "admin"
    USER = "user" 
    VIEWER = "viewer"

class ClearanceLevel(Enum):
    """Document sensitivity clearance levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    HIPAA_PHI = "hipaa_phi"

@dataclass
class User:
    username: str
    email: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    # Multi-tenant fields
    tenant_id: str = "huron"  # Default tenant
    dept_id: Optional[str] = None  # Primary department
    dept_ids: Optional[List[str]] = None  # All departments user can access
    clearance_level: ClearanceLevel = ClearanceLevel.INTERNAL

class AuthenticationManager:
    """Production-ready authentication system for VaultMind"""
    
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.token_expiry_hours = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))
        self._init_database()
        self._create_default_admin()
    
    def _init_database(self):
        """Initialize user database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            tenant_id TEXT DEFAULT 'huron',
            dept_id TEXT,
            clearance_level TEXT DEFAULT 'internal'
        )
        """)
        
        # Add new columns if they don't exist (for migration)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN tenant_id TEXT DEFAULT 'huron'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN dept_id TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN clearance_level TEXT DEFAULT 'internal'")
        except sqlite3.OperationalError:
            pass
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        conn.commit()
        conn.close()
    
    def _create_default_admin(self):
        """Create default admin user if none exists"""
        if not self.user_exists("admin"):
            self.create_user(
                username="admin",
                email="admin@vaultmind.ai",
                password="VaultMind2025!",  # Change in production
                role=UserRole.ADMIN
            )
            # Avoid non-ASCII characters to prevent encoding errors on some Windows consoles
            logger.info("Default admin user created: admin / VaultMind2025!")
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_user(self, username: str, email: str, password: str, role: UserRole) -> bool:
        """Create new user account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            
            cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
            """, (username, email, password_hash, role.value))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.IntegrityError:
            return False  # User already exists
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if account is locked
        cursor.execute("""
        SELECT * FROM users 
        WHERE username = ? AND is_active = 1
        """, (username,))
        
        user_data = cursor.fetchone()
        if not user_data:
            conn.close()
            return None
        
        # Check if account is temporarily locked
        if user_data[9]:  # locked_until
            locked_until = datetime.fromisoformat(user_data[9])
            if datetime.now() < locked_until:
                conn.close()
                return None
        
        # Verify password
        if self.verify_password(password, user_data[3]):
            # Reset failed attempts and update last login
            cursor.execute("""
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP, 
                failed_login_attempts = 0,
                locked_until = NULL
            WHERE username = ?
            """, (username,))
            
            conn.commit()
            conn.close()
            
            return User(
                username=user_data[1],
                email=user_data[2],
                role=UserRole(user_data[4]),
                created_at=datetime.fromisoformat(user_data[5]),
                last_login=datetime.now(),
                is_active=bool(user_data[7])
            )
        else:
            # Increment failed attempts
            failed_attempts = user_data[8] + 1
            locked_until = None
            
            # Lock account after 5 failed attempts for 30 minutes
            if failed_attempts >= 5:
                locked_until = datetime.now() + timedelta(minutes=30)
            
            cursor.execute("""
            UPDATE users 
            SET failed_login_attempts = ?,
                locked_until = ?
            WHERE username = ?
            """, (failed_attempts, locked_until.isoformat() if locked_until else None, username))
            
            conn.commit()
            conn.close()
            return None
    
    def generate_token(self, user: User, dept_id: Optional[str] = None) -> str:
        """Generate JWT token for authenticated user.
        
        Token includes multi-tenant claims:
        - tenant_id: The tenant organization
        - dept_id: Primary department for this session
        - dept_ids: All departments user can access
        - clearance_level: Document sensitivity clearance
        """
        # Use provided dept_id or fall back to user's primary dept
        session_dept = dept_id or user.dept_id
        
        payload = {
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            'iat': datetime.utcnow(),
            # Multi-tenant claims (Phase 1 requirement)
            'tenant_id': user.tenant_id,
            'dept_id': session_dept,
            'dept_ids': user.dept_ids or ([session_dept] if session_dept else []),
            'clearance_level': user.clearance_level.value if hasattr(user.clearance_level, 'value') else str(user.clearance_level),
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def user_exists(self, username: str) -> bool:
        """Check if user exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        exists = cursor.fetchone() is not None
        
        conn.close()
        return exists
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT username, email, role, created_at, last_login, is_active,
               tenant_id, dept_id, clearance_level
        FROM users WHERE username = ? AND is_active = 1
        """, (username,))
        
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            # Handle clearance level (may be None for legacy users)
            clearance = ClearanceLevel.INTERNAL
            if user_data[8]:
                try:
                    clearance = ClearanceLevel(user_data[8])
                except ValueError:
                    clearance = ClearanceLevel.INTERNAL
            
            return User(
                username=user_data[0],
                email=user_data[1],
                role=UserRole(user_data[2]),
                created_at=datetime.fromisoformat(user_data[3]),
                last_login=datetime.fromisoformat(user_data[4]) if user_data[4] else None,
                is_active=bool(user_data[5]),
                tenant_id=user_data[6] or 'huron',
                dept_id=user_data[7],
                clearance_level=clearance
            )
        return None
    
    def get_all_users(self) -> List[User]:
        """Get all users (admin only)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT username, email, role, created_at, last_login, is_active
        FROM users ORDER BY created_at DESC
        """)
        
        users = []
        for user_data in cursor.fetchall():
            users.append(User(
                username=user_data[0],
                email=user_data[1],
                role=UserRole(user_data[2]),
                created_at=datetime.fromisoformat(user_data[3]),
                last_login=datetime.fromisoformat(user_data[4]) if user_data[4] else None,
                is_active=bool(user_data[5])
            ))
        
        conn.close()
        return users
    
    def update_user_role(self, username: str, new_role: UserRole) -> bool:
        """Update user role (admin only)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            UPDATE users SET role = ? WHERE username = ?
            """, (new_role.value, username))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating user role: {e}")
            return False
    
    def deactivate_user(self, username: str) -> bool:
        """Deactivate user account (admin only)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            UPDATE users SET is_active = 0 WHERE username = ?
            """, (username,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deactivating user: {e}")
            return False

# Global authentication manager instance
auth_manager = AuthenticationManager()
