from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings  # noqa: E402
from backend.services.schema_migration_service import ensure_knowledge_governance_columns  # noqa: E402


async def _run(database_url: str) -> None:
    engine = create_async_engine(database_url, echo=False, future=True)
    try:
        await ensure_knowledge_governance_columns(engine)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply AgentForge policy governance schema columns.")
    parser.add_argument(
        "--database-url",
        default=settings.DB_URL,
        help="SQLAlchemy async database URL. Defaults to backend settings DB_URL.",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.database_url))
    print("Policy governance schema migration completed.")


if __name__ == "__main__":
    main()
