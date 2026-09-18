import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.services.marketplace_tool_adapter import MarketplaceToolAdapter
from plugin_marketplace import MarketplaceAPI
from plugin_marketplace.db.database import Base
from plugin_marketplace.exceptions import ToolBindingValidationError


@pytest.mark.asyncio
async def test_bind_and_get_tools_for_agent(tmp_path):
    db_path = tmp_path / "pm-binding.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()

    agent_id = str(uuid.uuid4())

    await api.bind_tools_to_agent(agent_id, ["builtin/echo"])
    tools = await api.get_tools_for_agent(agent_id)

    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "builtin/echo"

    await engine.dispose()


@pytest.mark.asyncio
async def test_bind_tools_accepts_bare_alias_name(tmp_path):
    db_path = tmp_path / "pm-binding-alias.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()

    agent_id = str(uuid.uuid4())

    await api.bind_tools_to_agent(agent_id, ["python_executor"])
    tools = await api.get_tools_for_agent(agent_id)

    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "builtin/python_executor"

    await engine.dispose()


@pytest.mark.asyncio
async def test_bind_tools_rejects_unknown_tool_ids(tmp_path):
    db_path = tmp_path / "pm-binding-invalid.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()

    with pytest.raises(ToolBindingValidationError) as exc_info:
        await api.bind_tools_to_agent(str(uuid.uuid4()), ["builtin/does_not_exist"])

    assert exc_info.value.missing_tool_ids == ["builtin/does_not_exist"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_assembler_syncs_legacy_config_tools_into_bindings(tmp_path):
    db_path = tmp_path / "pm-runtime-legacy-sync.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()
    adapter = MarketplaceToolAdapter(api)
    agent_id = str(uuid.uuid4())

    runtime = await adapter.resolve_agent_runtime(
        agent_id=agent_id,
        agent_config={
            "capability_flags": {"supports_tools": True},
            "constraints": {"max_steps": 6},
            "tools": ["python_executor"],
        },
        user_input="请调用 python_executor 计算。",
    )

    assert runtime.resolution_source == "legacy_config_sync"
    assert runtime.bound_tool_ids == ["builtin/python_executor"]
    assert runtime.resolved_tool_names == ["builtin/python_executor"]
    assert runtime.unavailable_requested_tools == []

    await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_assembler_applies_default_builtin_profile_for_tool_enabled_agents_when_tools_config_missing(tmp_path):
    db_path = tmp_path / "pm-runtime-default-profile.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()
    adapter = MarketplaceToolAdapter(api)

    runtime = await adapter.resolve_agent_runtime(
        agent_id=str(uuid.uuid4()),
        agent_config={
            "capability_flags": {"supports_tools": True},
            "constraints": {"max_steps": 6},
        },
        user_input="昨天白宫发生了什么？",
    )

    assert runtime.resolution_source == "default_builtin_profile"
    assert "builtin/websearch" in runtime.bound_tool_ids
    assert "builtin/calculate" in runtime.bound_tool_ids
    assert "builtin/websearch" in runtime.resolved_tool_names
    assert "builtin/calculate" in runtime.resolved_tool_names
    assert runtime.unavailable_requested_tools == []

    await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_assembler_defaults_missing_capability_flags_to_tool_enabled_when_tools_config_missing(tmp_path):
    db_path = tmp_path / "pm-runtime-default-capability.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()
    adapter = MarketplaceToolAdapter(api)

    runtime = await adapter.resolve_agent_runtime(
        agent_id=str(uuid.uuid4()),
        agent_config={
            "constraints": {"max_steps": 6},
        },
        user_input="昨天白宫发生了什么？",
    )

    assert runtime.supports_tools is True
    assert runtime.resolution_source == "default_builtin_profile"
    assert "builtin/websearch" in runtime.bound_tool_ids
    assert "builtin/websearch" in runtime.resolved_tool_names

    await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_assembler_treats_legacy_supports_tools_false_as_tool_enabled_when_tools_config_missing(tmp_path):
    db_path = tmp_path / "pm-runtime-legacy-false-capability.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()
    adapter = MarketplaceToolAdapter(api)

    runtime = await adapter.resolve_agent_runtime(
        agent_id=str(uuid.uuid4()),
        agent_config={
            "capability_flags": {"supports_tools": False},
            "constraints": {"max_steps": 6},
        },
        user_input="昨天白宫发生了什么？",
    )

    assert runtime.supports_tools is True
    assert runtime.resolution_source == "default_builtin_profile"
    assert "builtin/websearch" in runtime.bound_tool_ids

    await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_assembler_preserves_explicit_empty_tool_configuration(tmp_path):
    db_path = tmp_path / "pm-runtime-explicit-empty-tools.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()
    adapter = MarketplaceToolAdapter(api)

    runtime = await adapter.resolve_agent_runtime(
        agent_id=str(uuid.uuid4()),
        agent_config={
            "capability_flags": {"supports_tools": True},
            "constraints": {"max_steps": 6},
            "tools": [],
        },
        user_input="请总结一下今天的工作内容。",
    )

    assert runtime.resolution_source == "explicit_empty_tools"
    assert runtime.bound_tool_ids == []
    assert runtime.tool_schemas == []
    assert runtime.resolved_tool_names == []
    assert runtime.unavailable_requested_tools == []

    await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_assembler_ignores_stale_bindings_when_tools_config_explicitly_empty(tmp_path):
    db_path = tmp_path / "pm-runtime-explicit-empty-with-stale-bindings.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()
    adapter = MarketplaceToolAdapter(api)
    agent_id = str(uuid.uuid4())

    await api.bind_tools_to_agent(agent_id, ["builtin/websearch"])
    runtime = await adapter.resolve_agent_runtime(
        agent_id=agent_id,
        agent_config={
            "capability_flags": {"supports_tools": True},
            "tools": [],
        },
        user_input="请调用 websearch 查一下今天的新闻。",
    )

    assert runtime.resolution_source == "explicit_empty_tools"
    assert runtime.bound_tool_ids == []
    assert runtime.tool_schemas == []
    assert runtime.resolved_tool_names == []
    assert runtime.binding_drift["binding_only"] == ["builtin/websearch"]
    assert runtime.unavailable_requested_tools == ["builtin/websearch"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_runtime_assembler_reports_binding_drift_when_config_contains_invalid_tools(tmp_path):
    db_path = tmp_path / "pm-runtime-drift.db"
    database_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()
    adapter = MarketplaceToolAdapter(api)

    runtime = await adapter.resolve_agent_runtime(
        agent_id=str(uuid.uuid4()),
        agent_config={
            "capability_flags": {"supports_tools": True},
            "constraints": {"max_steps": 6},
            "tools": ["python_executor", "builtin/not_real"],
        },
        user_input="请调用 python_executor。",
    )

    assert runtime.resolution_source == "binding_drift"
    assert runtime.unresolved_tools == ["builtin/not_real"]
    assert runtime.tool_schemas == []
    assert runtime.binding_drift["config_only"] == ["builtin/python_executor"]
    assert runtime.unavailable_requested_tools == ["builtin/python_executor"]

    await engine.dispose()
