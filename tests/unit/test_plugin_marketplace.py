import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api.dependencies import get_current_user
from backend.models.schemas import AuthContext
from backend.services.authorization_service import authorization_service
from plugin_marketplace.db.database import Base


def _attach_auth_overrides(app: FastAPI, monkeypatch):
    async def _test_auth_context():
        return AuthContext(
            user_id="demo-user",
            team_id="00000000-0000-0000-0000-000000000001",
            auth_mode="test",
            request_id="req-test-marketplace",
            role="member",
            is_dev=False,
        )

    async def _allow(*args, **kwargs):
        return None

    app.dependency_overrides[get_current_user] = _test_auth_context
    monkeypatch.setattr(authorization_service, "ensure_extension_installation_scope", _allow)
    monkeypatch.setattr(authorization_service, "ensure_user_extension_ownership", _allow)
    monkeypatch.setattr(authorization_service, "ensure_agent_ownership", _allow)


@pytest.mark.asyncio
async def test_marketplace_seeds_manifests_and_executes_builtin_tool(tmp_path):
    from plugin_marketplace import MarketplaceAPI

    db_path = tmp_path / "marketplace.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()

    manifests = await api.list_extensions()
    manifest_ids = {item["id"] for item in manifests}
    assert {"github", "filesystem", "brave_search", "builtin"}.issubset(manifest_ids)

    tools = await api.list_extension_tools("builtin")
    tool_ids = {tool["id"] for tool in tools}
    assert "builtin/echo" in tool_ids
    assert "builtin/echo_tool" in tool_ids
    assert "builtin/python_executor" in tool_ids
    assert "builtin/websearch" in tool_ids
    assert "builtin/calculate" in tool_ids
    python_exec = next(tool for tool in tools if tool["id"] == "builtin/python_exec")
    websearch = next(tool for tool in tools if tool["id"] == "builtin/websearch")
    assert python_exec["risk_level"] == "high"
    assert python_exec["requires_confirmation"] is True
    assert python_exec["side_effect"] == "write"
    assert websearch["risk_level"] == "medium"
    assert websearch["side_effect"] == "external_read"
    assert "web_search" in websearch["domains"]

    schemas = await api.get_tool_schemas()
    schema_names = {tool["function"]["name"] for tool in schemas}
    assert "builtin/python_executor" in schema_names
    assert "builtin/websearch" in schema_names
    assert "builtin/calculate" in schema_names

    catalog_entries = await api.get_tool_catalog_entries(["builtin/python_exec", "builtin/websearch"])
    catalog_by_id = {entry["id"]: entry for entry in catalog_entries}
    assert catalog_by_id["builtin/python_exec"]["requires_confirmation"] is True
    assert catalog_by_id["builtin/websearch"]["domains"] == ["web_search"]

    user_id = str(uuid.uuid4())
    await api.install_extension("builtin", user_id, {})

    result = await api.execute_tool(
        "builtin/echo_tool",
        {"text": "hello"},
        context={"user_id": user_id},
    )
    payload = json.loads(result)
    assert payload["echo"] == "hello"

    result = await api.execute_tool(
        "builtin/calculate",
        {"expression": "(12 + 8) / 5"},
        context={"user_id": user_id},
    )
    payload = json.loads(result)
    assert payload["result"] == 4

    await engine.dispose()


def test_marketplace_router_lists_seeded_extensions(tmp_path, monkeypatch):
    from plugin_marketplace import MarketplaceAPI
    from plugin_marketplace.api.routes import create_router

    async def _build_api():
        db_path = tmp_path / "marketplace-api.db"
        database_url = f"sqlite+aiosqlite:///{db_path}"
        engine = create_async_engine(database_url, future=True)
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
        await api.initialize()
        return api, engine

    import asyncio

    api, engine = asyncio.run(_build_api())

    app = FastAPI()
    app.state.pm_api = api
    app.include_router(create_router())
    _attach_auth_overrides(app, monkeypatch)

    with TestClient(app) as client:
        response = client.get("/api/v1/marketplace/extensions")
        assert response.status_code == 200
        payload = response.json()
        ids = {item["id"] for item in payload}
        assert "github" in ids
        assert "builtin" in ids

    asyncio.run(engine.dispose())


def test_marketplace_router_tests_extension_configuration(tmp_path, monkeypatch):
    from plugin_marketplace import MarketplaceAPI
    from plugin_marketplace.api.routes import create_router

    async def _build_api():
        db_path = tmp_path / "marketplace-config-api.db"
        database_url = f"sqlite+aiosqlite:///{db_path}"
        engine = create_async_engine(database_url, future=True)
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
        await api.initialize()
        return api, engine

    import asyncio

    api, engine = asyncio.run(_build_api())

    app = FastAPI()
    app.state.pm_api = api
    app.include_router(create_router())
    _attach_auth_overrides(app, monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/marketplace/extensions/filesystem/test-connection",
            json={"config": {"root_path": "Z:\\does-not-exist"}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is False
        assert "Path does not exist" in payload["message"]

    asyncio.run(engine.dispose())


def test_marketplace_router_full_extension_lifecycle(tmp_path, monkeypatch):
    from plugin_marketplace import MarketplaceAPI
    from plugin_marketplace.api.routes import create_router

    async def _build_api():
        db_path = tmp_path / "marketplace-lifecycle-api.db"
        database_url = f"sqlite+aiosqlite:///{db_path}"
        engine = create_async_engine(database_url, future=True)
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
        await api.initialize()
        return api, engine

    import asyncio

    api, engine = asyncio.run(_build_api())

    app = FastAPI()
    app.state.pm_api = api
    app.include_router(create_router())
    _attach_auth_overrides(app, monkeypatch)
    agent_id = str(uuid.uuid4())

    with TestClient(app) as client:
        response = client.get("/api/v1/marketplace/extensions/builtin")
        assert response.status_code == 200
        extension = response.json()
        assert extension["id"] == "builtin"
        assert any(tool["id"] == "builtin/echo_tool" for tool in extension["tools"])

        response = client.get("/api/v1/marketplace/extensions/builtin/tools")
        assert response.status_code == 200
        tools = response.json()
        assert any(tool["id"] == "builtin/echo_tool" for tool in tools)

        response = client.post(
            "/api/v1/marketplace/extensions/builtin/install",
            json={"user_id": "demo-user", "config": {}},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "installed"

        response = client.get("/api/v1/marketplace/users/demo-user/extensions")
        assert response.status_code == 200
        user_extensions = response.json()
        assert any(item["extension_id"] == "builtin" for item in user_extensions)

        response = client.post(
            f"/api/v1/marketplace/agents/{agent_id}/tools/bind",
            json={"tool_ids": ["echo_tool"]},
        )
        assert response.status_code == 200
        assert response.json()["bound"] == 1

        response = client.get(f"/api/v1/marketplace/agents/{agent_id}/tools")
        assert response.status_code == 200
        agent_tools = response.json()["tools"]
        assert any(tool["function"]["name"] == "builtin/echo_tool" for tool in agent_tools)

        response = client.get("/api/v1/marketplace/tools/schemas")
        assert response.status_code == 200
        schemas = response.json()["tools"]
        assert any(tool["function"]["name"] == "builtin/echo_tool" for tool in schemas)

        response = client.post(
            "/api/v1/marketplace/tools/execute",
            json={
                "tool_id": "builtin/echo_tool",
                "arguments": {"text": "route hello"},
                "context": {"user_id": "demo-user"},
            },
        )
        assert response.status_code == 200
        assert json.loads(response.json()["result"])["echo"] == "route hello"

        response = client.delete(f"/api/v1/marketplace/agents/{agent_id}/tools/builtin/echo_tool")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        response = client.get(f"/api/v1/marketplace/agents/{agent_id}/tools")
        assert response.status_code == 200
        assert response.json()["tools"] == []

        response = client.delete("/api/v1/marketplace/extensions/builtin/uninstall?user_id=demo-user")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        response = client.get("/api/v1/marketplace/users/demo-user/extensions")
        assert response.status_code == 200
        assert response.json() == []

    asyncio.run(engine.dispose())


def test_marketplace_router_rejects_unknown_tool_bindings(tmp_path, monkeypatch):
    from plugin_marketplace import MarketplaceAPI
    from plugin_marketplace.api.routes import create_router

    async def _build_api():
        db_path = tmp_path / "marketplace-invalid-bind-api.db"
        database_url = f"sqlite+aiosqlite:///{db_path}"
        engine = create_async_engine(database_url, future=True)
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
        await api.initialize()
        return api, engine

    import asyncio

    api, engine = asyncio.run(_build_api())

    app = FastAPI()
    app.state.pm_api = api
    app.include_router(create_router())
    _attach_auth_overrides(app, monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/marketplace/agents/{uuid.uuid4()}/tools/bind",
            json={"tool_ids": ["builtin/not_real"]},
        )
        assert response.status_code == 422
        assert "Unknown tool ids" in response.json()["detail"]

    asyncio.run(engine.dispose())


@pytest.mark.asyncio
async def test_marketplace_initialization_registers_adapters_for_seeded_extensions(tmp_path):
    from plugin_marketplace import MarketplaceAPI

    db_path = tmp_path / "marketplace-install.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()

    assert {"builtin", "github", "filesystem", "brave_search"}.issubset(set(api._adapters.keys()))

    await engine.dispose()


@pytest.mark.asyncio
async def test_extension_config_fields_and_connection_validation(tmp_path):
    from plugin_marketplace import MarketplaceAPI

    db_path = tmp_path / "marketplace-config.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()

    extensions = await api.list_extensions()
    filesystem = next(item for item in extensions if item["id"] == "filesystem")
    assert any(field["key"] == "root_path" for field in filesystem["config_fields"])

    result = await api.test_extension_connection("filesystem", {"root_path": "Z:\\does-not-exist"})
    assert result["ok"] is False
    assert "Path does not exist" in result["message"]

    await engine.dispose()
