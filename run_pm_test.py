#!/usr/bin/env python3
"""Standalone functional test runner for plugin_marketplace."""

import asyncio
import json
import os
import sys
import tempfile
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

sys.path.insert(0, ".")
sys.path.insert(0, "./backend")

from plugin_marketplace.db.database import Base


async def run_tests():
    db_path = os.path.join(tempfile.gettempdir(), "test_marketplace.db")
    if os.path.exists(db_path):
        os.unlink(db_path)

    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from plugin_marketplace import MarketplaceAPI
    from plugin_marketplace.api.routes import create_router

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()

    manifests = await api.list_extensions()
    manifest_ids = {item["id"] for item in manifests}
    print(f"Extensions found: {manifest_ids}")
    expected = {"github", "filesystem", "brave_search", "builtin"}
    missing = expected - manifest_ids
    assert expected.issubset(manifest_ids), f"Missing extensions: {missing}"
    print("[PASS] All 4 extensions seeded")

    user_id = str(uuid.uuid4())
    await api.install_extension("builtin", user_id, {})
    tools = await api.list_extension_tools("builtin")
    tool_ids = {tool["id"] for tool in tools}
    print(f"Builtin tools: {tool_ids}")
    assert "builtin/echo" in tool_ids, f"builtin/echo not found in {tool_ids}"
    print("[PASS] builtin/echo tool registered")

    result = await api.execute_tool("builtin/echo", {"text": "hello"}, context={"user_id": user_id})
    payload = json.loads(result)
    print(f"Echo result: {payload}")
    assert payload["echo"] == "hello", f"Expected hello, got {payload}"
    print("[PASS] builtin/echo executed successfully")

    app = FastAPI()
    app.state.pm_api = api
    app.include_router(create_router())

    with TestClient(app) as client:
        response = client.get("/api/v1/marketplace/extensions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        payload = response.json()
        ids = {item["id"] for item in payload}
        print(f"Router extensions: {ids}")
        assert "github" in ids and "builtin" in ids, f"Missing extensions in router response: {ids}"
        print("[PASS] Router /api/v1/marketplace/extensions returns correct data")

    await engine.dispose()
    print("\n[PASS] ALL TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(run_tests())
