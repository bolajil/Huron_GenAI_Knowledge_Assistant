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

# ─── Azure AD / OIDC ─────────────────────────────────────────────────────────
OIDC_CLIENT_ID     = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_AUTHORITY     = os.getenv("OIDC_AUTHORITY", "")   # https://login.microsoftonline.com/{tenant-id}
OIDC_REDIRECT_URI  = os.getenv("OIDC_REDIRECT_URI", "http://localhost:8004/api/v1/auth/oidc/callback")
FRONTEND_URL       = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ─── Workday ─────────────────────────────────────────────────────────────────
WORKDAY_BASE_URL      = os.getenv("WORKDAY_BASE_URL", "")
WORKDAY_TENANT        = os.getenv("WORKDAY_TENANT", "")
WORKDAY_CLIENT_ID     = os.getenv("WORKDAY_CLIENT_ID", "")
WORKDAY_CLIENT_SECRET = os.getenv("WORKDAY_CLIENT_SECRET", "")

# ─── Demo / Mock Mode ────────────────────────────────────────────────────────
WORKDAY_MOCK_MODE    = os.getenv("WORKDAY_MOCK_MODE", "false").lower() == "true"
SHAREPOINT_MOCK_MODE = os.getenv("SHAREPOINT_MOCK_MODE", "false").lower() == "true"

# ─── Teams Bot ───────────────────────────────────────────────────────────────
TEAMS_APP_ID     = os.getenv("TEAMS_APP_ID", "")
TEAMS_APP_SECRET = os.getenv("TEAMS_APP_SECRET", "")

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
    pinecone_index: str        = PINECONE_INDEX
    oidc_client_id: str        = OIDC_CLIENT_ID
    oidc_client_secret: str    = OIDC_CLIENT_SECRET
    oidc_authority: str        = OIDC_AUTHORITY
    oidc_redirect_uri: str     = OIDC_REDIRECT_URI
    frontend_url: str          = FRONTEND_URL
    workday_base_url: str      = WORKDAY_BASE_URL
    workday_tenant: str        = WORKDAY_TENANT
    workday_client_id: str     = WORKDAY_CLIENT_ID
    workday_client_secret: str = WORKDAY_CLIENT_SECRET
    workday_mock_mode: bool    = WORKDAY_MOCK_MODE
    sharepoint_mock_mode: bool = SHAREPOINT_MOCK_MODE
    teams_app_id: str          = TEAMS_APP_ID
    teams_app_secret: str      = TEAMS_APP_SECRET


settings = Settings()
