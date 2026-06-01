"""
Application configuration and environment variables.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path

from dotenv import load_dotenv

# ─── Load Environment Variables ──────────────────────────────────────────────
_ROOT_DIR = Path(__file__).parent.parent.parent
load_dotenv(_ROOT_DIR / ".env", override=False)
load_dotenv(_ROOT_DIR / "backend" / ".env", override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Environment ─────────────────────────────────────────────────────────────
APP_ENV = os.getenv("APP_ENV", "development")

# ─── JWT Configuration ───────────────────────────────────────────────────────
_jwt_secret_raw = os.getenv("JWT_SECRET_KEY", "")

if not _jwt_secret_raw:
    if APP_ENV in ("production", "prod", "staging"):
        raise RuntimeError(
            "FATAL: JWT_SECRET_KEY environment variable is required in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    _jwt_secret_raw = "local-dev-only-not-for-production"
    logger.warning("JWT_SECRET_KEY not set — using insecure default (local dev only)")

SECRET_KEY = _jwt_secret_raw
ALGORITHM = "HS256"
TOKEN_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "8"))

# ─── MCP Encryption ──────────────────────────────────────────────────────────
MCP_ENCRYPTION_KEY = os.getenv("MCP_ENCRYPTION_KEY", "")

# ─── Database ────────────────────────────────────────────────────────────────
_default_db = str(Path(__file__).parent.parent / "data" / "huron.db")
DB_PATH = Path(os.getenv("SQLITE_DB_PATH", _default_db))
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── Vector Backend ──────────────────────────────────────────────────────────
VECTOR_BACKEND = os.getenv(
    "VECTOR_BACKEND",
    "pinecone" if os.getenv("PINECONE_API_KEY") else "faiss",
)
os.environ.setdefault("VECTOR_BACKEND", VECTOR_BACKEND)

# ─── Redis ───────────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "")

# ─── OpenAI ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "huron-enterprise-knowledge")

# ─── Settings Object ─────────────────────────────────────────────────────────
class Settings:
    """Application settings container."""
    
    app_env: str = APP_ENV
    secret_key: str = SECRET_KEY
    algorithm: str = ALGORITHM
    token_hours: int = TOKEN_HOURS
    mcp_encryption_key: str = MCP_ENCRYPTION_KEY
    database_url: str = DATABASE_URL
    db_path: Path = DB_PATH
    vector_backend: str = VECTOR_BACKEND
    redis_url: str = REDIS_URL
    openai_api_key: str = OPENAI_API_KEY
    pinecone_api_key: str = PINECONE_API_KEY
    pinecone_index: str = PINECONE_INDEX


settings = Settings()
