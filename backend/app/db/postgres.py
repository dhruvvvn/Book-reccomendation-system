"""
PostgreSQL Database Connection

Async database connection using SQLAlchemy with asyncpg driver.
Provides session management and connection pooling.

Note: This is a stub for future implementation. Currently,
book metadata is stored alongside the FAISS index for simplicity.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for ORM models."""
    pass


# Engine and session factory (initialized lazily)
_engine = None
_session_factory = None


async def get_engine():
    """
    Get or create the async database engine.
    
    Uses lazy initialization to avoid connection attempts
    when database is not configured.
    """
    global _engine
    
    if _engine is None:
        settings = get_settings()
        
        if not settings.database_url:
            raise ValueError(
                "DATABASE_URL not configured. "
                "Set it in .env or environment variables."
            )
        
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,  # Log SQL in debug mode
            pool_pre_ping=True,   # Validate connections
            pool_size=5,
            max_overflow=10
        )
    
    return _engine


async def get_session_factory():
    """Get or create the async session factory."""
    global _session_factory
    
    if _session_factory is None:
        engine = await get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting a database session.
    
    Usage:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    factory = await get_session_factory()
    
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database tables.
    
    Called during application startup to create tables
    if they don't exist.
    """
    engine = await get_engine()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    
    Called during application shutdown.
    """
    global _engine, _session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
