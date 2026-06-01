"""API route modules."""

from .auth import router as auth_router
from .admin import router as admin_router
from .health import router as health_router

__all__ = [
    "auth_router",
    "admin_router", 
    "health_router",
]
