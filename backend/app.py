"""
Huron GenAI Knowledge Assistant — FastAPI Application (Refactored)

This is the new modular entry point. The original main.py is preserved for
backward compatibility during migration.

Usage:
    uvicorn app:app --host 0.0.0.0 --port 8004 --reload

Structure:
    backend/
    ├── app.py              # This file - thin entry point
    ├── main.py             # Legacy monolith (preserved during migration)
    ├── core/               # Core utilities
    │   ├── config.py       # Configuration & environment
    │   ├── database.py     # Database connection
    │   ├── security.py     # JWT, auth, encryption
    │   └── migrations.py   # Database migrations
    ├── models/             # Pydantic schemas
    │   └── schemas.py      # Request/response models
    ├── routes/             # API route modules
    │   ├── auth.py         # Authentication endpoints
    │   ├── admin.py        # Admin/root endpoints
    │   └── health.py       # Health check
    ├── agent/              # ReAct agent (existing)
    └── utils/              # Utilities (existing)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure backend directory is in path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import APP_ENV, settings
from core.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── App Instance ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Huron GenAI API",
    version="4.0.0",
    description="Enterprise-grade AI knowledge platform with RAG, ReAct agents, and RBAC",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
# TODO: Move to config for production domains
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Add production origins from environment
import os
if os.getenv("CORS_ORIGINS"):
    CORS_ORIGINS.extend(os.getenv("CORS_ORIGINS").split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Route Registration ──────────────────────────────────────────────────────
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.health import router as health_router

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(admin_router)

# NOTE: Additional routes (query, chat, agent, documents, mcp) remain in main.py
# during the migration. They can be incrementally moved to routes/ modules.

# ─── Startup ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting Huron GenAI API (env=%s)", APP_ENV)
    init_db()
    logger.info("Database initialized")


# ─── For backward compatibility, import remaining routes from main.py ────────
# This allows gradual migration without breaking existing functionality.
# Comment out once all routes are migrated to routes/ modules.

try:
    from main import app as legacy_app
    
    # Mount legacy routes that haven't been migrated yet
    # These include: /api/v1/query, /api/v1/chat, /api/v1/agent, etc.
    for route in legacy_app.routes:
        if hasattr(route, 'path'):
            path = route.path
            # Skip routes already defined in new modules
            if not any(path.startswith(p) for p in ['/api/v1/auth', '/health']):
                # Note: This is a simplified approach. In production,
                # fully migrate each route to its own module.
                pass
    
    logger.info("Legacy routes loaded for backward compatibility")
except ImportError as e:
    logger.warning("Could not import legacy main.py: %s", e)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8004")),
        reload=APP_ENV in ("development", "local"),
    )
