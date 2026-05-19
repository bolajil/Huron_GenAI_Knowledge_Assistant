"""
Huron GenAI Knowledge Assistant - Database Configuration
Production-grade database layer with PostgreSQL support for 20k+ users

Supports:
- SQLite for local development
- PostgreSQL for production (20,000+ concurrent users)
- Connection pooling via SQLAlchemy
- Async support for FastAPI

Author: Production Scalability Team
Date: May 2026
"""

import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool, NullPool

logger = logging.getLogger(__name__)

# SQLAlchemy Base for models
Base = declarative_base()


class DatabaseConfig:
    """Database configuration for different environments."""
    
    def __init__(self):
        self.env = os.getenv("ENVIRONMENT", "development")
        self.is_production = self.env == "production"
        
    @property
    def database_url(self) -> str:
        """Get database URL based on environment."""
        if self.is_production:
            # PostgreSQL for production
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            user = os.getenv("POSTGRES_USER", "huron")
            password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
            database = os.getenv("POSTGRES_DB", "huron_knowledge")
            
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        else:
            # SQLite for development
            db_path = os.getenv("SQLITE_PATH", "data/users.db")
            return f"sqlite:///{db_path}"
    
    @property
    def async_database_url(self) -> str:
        """Get async database URL for FastAPI."""
        if self.is_production:
            # asyncpg for PostgreSQL
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            user = os.getenv("POSTGRES_USER", "huron")
            password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
            database = os.getenv("POSTGRES_DB", "huron_knowledge")
            
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        else:
            # aiosqlite for development
            db_path = os.getenv("SQLITE_PATH", "data/users.db")
            return f"sqlite+aiosqlite:///{db_path}"
    
    @property
    def pool_settings(self) -> dict:
        """Connection pool settings for production scale."""
        if self.is_production:
            return {
                "poolclass": QueuePool,
                "pool_size": 20,  # Base connections
                "max_overflow": 30,  # Additional connections under load
                "pool_timeout": 30,  # Seconds to wait for connection
                "pool_recycle": 1800,  # Recycle connections after 30 min
                "pool_pre_ping": True,  # Test connections before use
            }
        else:
            return {
                "poolclass": NullPool,  # No pooling for SQLite
            }


# Global configuration
db_config = DatabaseConfig()


def get_engine():
    """Create SQLAlchemy engine with appropriate settings."""
    engine = create_engine(
        db_config.database_url,
        **db_config.pool_settings,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    )
    
    # SQLite-specific settings
    if "sqlite" in db_config.database_url:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    return engine


# Create engine and session factory
engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for database session (non-FastAPI usage)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_database():
    """Initialize database tables."""
    from app.auth.models import User, UserSession, Department, AuditLog
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized: {db_config.database_url.split('@')[-1] if '@' in db_config.database_url else db_config.database_url}")


def health_check() -> dict:
    """Check database connectivity."""
    try:
        with get_db_context() as db:
            db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "postgresql" if db_config.is_production else "sqlite",
            "environment": db_config.env,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database": "postgresql" if db_config.is_production else "sqlite",
        }
