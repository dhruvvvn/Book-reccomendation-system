"""
API v1 Router

Aggregates all endpoint routers into a single router for mounting.
This pattern allows easy versioning - when v2 is needed, create a new
router file without modifying existing v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, books, chat, discover, health

api_router = APIRouter()

# Include all endpoint routers with appropriate prefixes and tags
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"]
)

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    discover.router,
    prefix="/discover",
    tags=["Discover"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat"]
)

api_router.include_router(
    books.router,
    prefix="/books",
    tags=["Books"]
)

