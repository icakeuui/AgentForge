from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

import pytest

from backend.services.schema_migration_service import ensure_knowledge_governance_columns


@pytest.mark.asyncio
async def test_policy_governance_migration_adds_missing_sqlite_columns(tmp_path):
    db_path = tmp_path / "migration.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE knowledge_documents (id VARCHAR PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE knowledge_chunks (id VARCHAR PRIMARY KEY)"))
        await conn.execute(text("CREATE TABLE pm_tools (id VARCHAR PRIMARY KEY)"))

    await ensure_knowledge_governance_columns(engine)

    async with engine.begin() as conn:
        tables = await conn.run_sync(_read_columns)

    assert "document_type" in tables["knowledge_documents"]
    assert "metadata" in tables["knowledge_documents"]
    assert "article_no" in tables["knowledge_chunks"]
    assert "section_path" in tables["knowledge_chunks"]
    assert "risk_level" in tables["pm_tools"]
    assert "requires_confirmation" in tables["pm_tools"]

    await engine.dispose()


def _read_columns(sync_conn):
    inspector = inspect(sync_conn)
    return {
        table_name: {column["name"] for column in inspector.get_columns(table_name)}
        for table_name in ["knowledge_documents", "knowledge_chunks", "pm_tools"]
    }
