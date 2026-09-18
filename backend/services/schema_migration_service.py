from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.core.logging import logger


KNOWLEDGE_DOCUMENT_COLUMNS = {
    "document_type": {"sqlite": "VARCHAR DEFAULT 'other'", "postgresql": "VARCHAR DEFAULT 'other'"},
    "source_filename": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "source_mime_type": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "source_hash": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "version_label": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "effective_from": {"sqlite": "DATETIME", "postgresql": "TIMESTAMP WITH TIME ZONE"},
    "effective_to": {"sqlite": "DATETIME", "postgresql": "TIMESTAMP WITH TIME ZONE"},
    "status": {"sqlite": "VARCHAR DEFAULT 'ACTIVE'", "postgresql": "VARCHAR DEFAULT 'ACTIVE'"},
    "metadata": {"sqlite": "JSON DEFAULT '{}'", "postgresql": "JSONB DEFAULT '{}'::jsonb"},
    "embedding_status": {"sqlite": "VARCHAR DEFAULT 'pending'", "postgresql": "VARCHAR DEFAULT 'pending'"},
    "embedding_provider": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "embedding_model_name": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "embedding_dimensions": {"sqlite": "INTEGER", "postgresql": "INTEGER"},
    "embedding_error": {"sqlite": "TEXT", "postgresql": "TEXT"},
    "chunk_count": {"sqlite": "INTEGER DEFAULT 0", "postgresql": "INTEGER DEFAULT 0"},
}

KNOWLEDGE_CHUNK_COLUMNS = {
    "chunk_type": {"sqlite": "VARCHAR DEFAULT 'plain'", "postgresql": "VARCHAR DEFAULT 'plain'"},
    "section_path": {"sqlite": "JSON DEFAULT '[]'", "postgresql": "JSONB DEFAULT '[]'::jsonb"},
    "article_no": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "article_label": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "page_no": {"sqlite": "INTEGER", "postgresql": "INTEGER"},
    "start_char": {"sqlite": "INTEGER", "postgresql": "INTEGER"},
    "end_char": {"sqlite": "INTEGER", "postgresql": "INTEGER"},
    "metadata": {"sqlite": "JSON DEFAULT '{}'", "postgresql": "JSONB DEFAULT '{}'::jsonb"},
    "embedding": {"sqlite": "JSON", "postgresql": "JSONB"},
    "embedding_status": {"sqlite": "VARCHAR DEFAULT 'pending'", "postgresql": "VARCHAR DEFAULT 'pending'"},
    "embedding_model_name": {"sqlite": "VARCHAR", "postgresql": "VARCHAR"},
    "embedding_dimensions": {"sqlite": "INTEGER", "postgresql": "INTEGER"},
    "vector_point_id": {"sqlite": "VARCHAR(64)", "postgresql": "VARCHAR(64)"},
}

PM_TOOL_RISK_COLUMNS = {
    "risk_level": {"sqlite": "VARCHAR DEFAULT 'medium'", "postgresql": "VARCHAR DEFAULT 'medium'"},
    "side_effect": {"sqlite": "VARCHAR DEFAULT 'read'", "postgresql": "VARCHAR DEFAULT 'read'"},
    "requires_confirmation": {"sqlite": "BOOLEAN DEFAULT 0", "postgresql": "BOOLEAN DEFAULT false"},
    "allowed_intents": {"sqlite": "JSON", "postgresql": "JSONB"},
    "domains": {"sqlite": "JSON", "postgresql": "JSONB"},
    "requires_auth_scope": {"sqlite": "JSON", "postgresql": "JSONB"},
    "max_calls_per_run": {"sqlite": "INTEGER DEFAULT 2", "postgresql": "INTEGER DEFAULT 2"},
    "timeout_ms": {"sqlite": "INTEGER DEFAULT 10000", "postgresql": "INTEGER DEFAULT 10000"},
    "returns_sensitive_data": {"sqlite": "BOOLEAN DEFAULT 0", "postgresql": "BOOLEAN DEFAULT false"},
    "audit_payload_level": {"sqlite": "VARCHAR DEFAULT 'summary'", "postgresql": "VARCHAR DEFAULT 'summary'"},
}

EMAIL_VERIFICATION_COLUMNS = {
    "send_status": {"sqlite": "VARCHAR DEFAULT 'PENDING'", "postgresql": "VARCHAR DEFAULT 'PENDING'"},
    "send_attempts": {"sqlite": "INTEGER DEFAULT 0", "postgresql": "INTEGER DEFAULT 0"},
    "verification_attempts": {"sqlite": "INTEGER DEFAULT 0", "postgresql": "INTEGER DEFAULT 0"},
    "sent_at": {"sqlite": "DATETIME", "postgresql": "TIMESTAMP WITH TIME ZONE"},
    "last_send_error": {"sqlite": "TEXT", "postgresql": "TEXT"},
    "invalidated_at": {"sqlite": "DATETIME", "postgresql": "TIMESTAMP WITH TIME ZONE"},
}


async def ensure_knowledge_governance_columns(engine: AsyncEngine) -> None:
    """Add nullable Phase 3 knowledge governance columns for DBs without Alembic."""

    async with engine.begin() as conn:
        await conn.run_sync(_ensure_columns_sync)


async def ensure_auth_columns(engine: AsyncEngine) -> None:
    """Add auth verification columns for DBs without Alembic."""

    async with engine.begin() as conn:
        await conn.run_sync(_ensure_auth_columns_sync)


def _ensure_columns_sync(sync_conn) -> None:
    inspector = inspect(sync_conn)
    dialect_name = sync_conn.dialect.name
    table_names = set(inspector.get_table_names())
    if "knowledge_documents" in table_names:
        _add_missing_columns(sync_conn, inspector, "knowledge_documents", KNOWLEDGE_DOCUMENT_COLUMNS, dialect_name)
    if "knowledge_chunks" in table_names:
        _add_missing_columns(sync_conn, inspector, "knowledge_chunks", KNOWLEDGE_CHUNK_COLUMNS, dialect_name)
    if "pm_tools" in table_names:
        _add_missing_columns(sync_conn, inspector, "pm_tools", PM_TOOL_RISK_COLUMNS, dialect_name)
def _ensure_auth_columns_sync(sync_conn) -> None:
    inspector = inspect(sync_conn)
    dialect_name = sync_conn.dialect.name
    table_names = set(inspector.get_table_names())
    if "email_verification_codes" in table_names:
        _add_missing_columns(sync_conn, inspector, "email_verification_codes", EMAIL_VERIFICATION_COLUMNS, dialect_name)


def _add_missing_columns(sync_conn, inspector, table_name: str, columns: dict[str, dict[str, str]], dialect_name: str) -> None:
    existing = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, ddl_types in columns.items():
        if column_name in existing:
            continue
        ddl_type = ddl_types.get(dialect_name) or ddl_types["sqlite"]
        ddl = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}"
        logger.bind(event="schema_migration", table=table_name, column=column_name).info("Adding knowledge governance column")
        sync_conn.execute(text(ddl))
