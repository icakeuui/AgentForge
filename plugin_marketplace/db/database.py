"""
plugin_marketplace.db.database
Async SQLAlchemy database setup for plugin marketplace.
Can work standalone or integrated with the AgentForge backend.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from plugin_marketplace.config import settings


class PMBase(DeclarativeBase):
    """Standalone declarative base for plugin marketplace."""
    pass


def _get_orm_base():
    """
    Get the ORM Base to use.
    Always uses PMBase so PM models register with it.
    In integrated mode with full AgentForge backend, the backend
    should use a separate Base for its own models.
    """
    return PMBase


# Resolve at import time
Base = _get_orm_base()


def create_engine_and_session(
    database_url: Optional[str] = None,
):
    """
    Create async engine and session factory.

    Returns:
        tuple: (engine, async_sessionmaker)
    """
    url = database_url or settings.database_url
    engine = create_async_engine(url, echo=False, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def init_db(engine) -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db(engine) -> None:
    """Close database connections."""
    await engine.dispose()


@asynccontextmanager
async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Context manager for a database session."""
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


__all__ = [
    "session_scope",  # alias for get_db_session
    "Base",
    "PMBase",
    "create_engine_and_session",
    "init_db",
    "close_db",
    "get_db_session",
]

# Alias for backwards compatibility
session_scope = get_db_session

