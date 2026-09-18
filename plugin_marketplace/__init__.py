"""
plugin_marketplace
Plugin marketplace and tool extension system for AgentForge.

Usage:
    from plugin_marketplace import MarketplaceAPI

    api = MarketplaceAPI(database_url="sqlite+aiosqlite:///./pm.db", ...)
    await api.initialize()
    await api.execute_tool("builtin/echo", {"text": "hello"}, context={"user_id": "u1"})
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from plugin_marketplace.config import settings
from plugin_marketplace.db import (
    create_engine_and_session,
    init_db,
    close_db,
    PMExtension,
    PMUserExtension,
)
from plugin_marketplace.core import (
    ToolRegistry,
    ToolExecutorImpl,
    ExtensionManager,
    AgentToolBindingService,
)
from plugin_marketplace.adapters import BuiltinAdapter, MCPAdapter, APIAdapter
from plugin_marketplace.marketplace.service import MarketplaceService
from plugin_marketplace.marketplace.manifest import ManifestParser
from plugin_marketplace.interfaces import ToolType

logger = logging.getLogger(__name__)


class MarketplaceAPI:
    """
    Main API for the plugin marketplace.

    Usage:
        api = MarketplaceAPI(database_url="...", session_factory=...)
        await api.initialize()
        result = await api.execute_tool("builtin/echo", {"text": "hi"}, context={...})
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        session_factory=None,
        settings_obj=None,
    ):
        self.database_url = database_url or settings.database_url
        self.settings = settings_obj or settings
        self._engine = None
        self._session_factory = session_factory
        self._adapters: Dict[str, Any] = {}
        self._extension_index: Dict[str, Any] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Load manifests, seed DB, start adapters."""
        if self._initialized:
            return

        # Create engine if not provided
        if self._session_factory is None:
            self._engine, self._session_factory = create_engine_and_session(self.database_url)
            await init_db(self._engine)

        # Load manifests
        parser = ManifestParser()
        manifests_path = Path(self.settings.manifest_dir)
        if manifests_path.exists():
            manifests = parser.load_directory(manifests_path)
        else:
            manifests = []
            logger.warning("Manifests path %s does not exist, skipping manifest load", manifests_path)

        # Marketplace service seeds extensions
        self._marketplace_service = MarketplaceService(self._session_factory, manifests)
        await self._marketplace_service.seed_extensions()

        extension_records = await self._marketplace_service.list_extension_records()
        self._extension_index = {extension.id: extension for extension in extension_records}
        self._adapters = self._build_adapter_factories(extension_records)
        await self._materialize_tool_catalog(extension_records)

        self._initialized = True
        logger.info("MarketplaceAPI initialized with %d manifests", len(manifests))

    def _build_adapter_factories(self, extensions: List[Any]) -> Dict[str, Any]:
        factories: Dict[str, Any] = {}
        for extension in extensions:
            factory = self._build_adapter_factory(extension)
            if factory is not None:
                factories[extension.id] = factory
        return factories

    def _build_adapter_factory(self, extension) -> Any | None:
        tool_type = extension.tool_type
        if tool_type == ToolType.BUILTIN.value:
            return lambda user_config=None, ext=extension: BuiltinAdapter(ext.id, user_config or {})
        if tool_type == ToolType.MCP.value:
            return lambda user_config=None, ext=extension: MCPAdapter(ext, user_config or {})
        if tool_type == ToolType.API.value:
            return lambda user_config=None, ext=extension: APIAdapter(ext, user_config or {})
        logger.warning("Unsupported extension tool_type=%s for extension=%s", tool_type, extension.id)
        return None

    def _create_adapter(self, extension_id: str, user_config: Optional[Dict[str, Any]] = None) -> Any:
        factory = self._adapters.get(extension_id)
        if not factory:
            raise ValueError(f"No adapter found for extension: {extension_id}")
        return factory(user_config or {})

    async def _materialize_tool_catalog(self, extensions: List[Any]) -> None:
        registry = ToolRegistry(self._session_factory)
        for extension in extensions:
            descriptors = await self._discover_catalog_descriptors(extension)
            if not descriptors:
                continue
            await registry.upsert_tools(extension.id, descriptors)

    async def _discover_catalog_descriptors(self, extension: Any) -> List[Any]:
        manifest = extension.manifest or {}
        manifest_tools = manifest.get("tools") or []
        if extension.tool_type == ToolType.BUILTIN.value:
            adapter = self._create_adapter(extension.id, {})
        elif manifest_tools:
            adapter = self._create_adapter(extension.id, {})
        else:
            return []

        try:
            return await adapter.list_tools()
        except Exception as exc:
            logger.warning("Failed to materialize tools for extension %s: %s", extension.id, exc)
            return []

    async def _get_user_extension_config(self, extension_id: str, user_id: str) -> Dict[str, Any]:
        if not self._session_factory:
            return {}
        async with self._session_factory() as session:
            result = await session.execute(
                select(PMUserExtension).where(
                    PMUserExtension.extension_id == extension_id,
                    PMUserExtension.user_id == user_id,
                )
            )
            record = result.scalar_one_or_none()
            return record.config or {} if record else {}

    def _validate_extension_config(self, extension_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        extension = self._extension_index.get(extension_id)
        if extension is None:
            raise ValueError(f"Extension not found: {extension_id}")

        config = config or {}
        manifest = extension.manifest or {}
        config_fields = manifest.get("config", [])
        missing_fields = [
            field["key"]
            for field in config_fields
            if field.get("required") and not config.get(field["key"])
        ]

        if missing_fields:
            return {
                "ok": False,
                "message": "Missing required configuration fields.",
                "missing_fields": missing_fields,
            }

        if extension_id == "filesystem":
            root_path = config.get("root_path")
            if not root_path:
                return {"ok": False, "message": "root_path is required.", "missing_fields": ["root_path"]}
            if not os.path.isdir(root_path):
                return {"ok": False, "message": f"Path does not exist or is not a directory: {root_path}", "missing_fields": []}

        return {"ok": True, "message": "Configuration looks valid.", "missing_fields": []}

    async def execute_tool(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute a tool by ID (format: 'extension_id/tool_name')."""
        if not self._initialized:
            await self.initialize()

        parts = tool_id.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid tool_id format: {tool_id}. Expected 'extension_id/tool_name'")
        extension_id, tool_name = parts

        user_id = context.get("user_id") if context else None
        user_config = {}
        if user_id:
            user_config = await self._get_user_extension_config(extension_id, user_id)

        adapter = self._create_adapter(extension_id, user_config)
        try:
            if extension_id != "builtin":
                await adapter.install()
            return await adapter.execute(tool_name, arguments)
        finally:
            if extension_id != "builtin":
                await adapter.uninstall()

    async def get_tools_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all tools bound to an agent, in OpenAI function-calling schema."""
        if not self._initialized:
            await self.initialize()
        binding = AgentToolBindingService(self._session_factory)
        return await binding.get_agent_tools(agent_id)

    async def bind_tools_to_agent(self, agent_id: str, tool_ids: List[str]) -> None:
        """Bind tools to an agent."""
        if not self._initialized:
            await self.initialize()
        binding = AgentToolBindingService(self._session_factory)
        return await binding.bind_tools(agent_id, tool_ids)

    async def replace_agent_tools(self, agent_id: str, tool_ids: List[str]) -> Any:
        """Replace all agent tool bindings with the requested set."""
        if not self._initialized:
            await self.initialize()
        binding = AgentToolBindingService(self._session_factory)
        return await binding.replace_tools(agent_id, tool_ids)

    async def unbind_tools_from_agent(self, agent_id: str, tool_ids: List[str]) -> None:
        """Unbind tools from an agent."""
        if not self._initialized:
            await self.initialize()
        binding = AgentToolBindingService(self._session_factory)
        return await binding.unbind_tools(agent_id, tool_ids)

    async def validate_tool_ids(self, tool_ids: List[str]) -> Any:
        if not self._initialized:
            await self.initialize()
        binding = AgentToolBindingService(self._session_factory)
        return await binding.resolve_tool_ids(tool_ids)

    async def get_agent_tool_ids(self, agent_id: str) -> List[str]:
        if not self._initialized:
            await self.initialize()
        binding = AgentToolBindingService(self._session_factory)
        return await binding.get_agent_tool_ids(agent_id)

    async def list_extensions(self) -> List[Dict[str, Any]]:
        """List all available extensions."""
        if not self._initialized:
            await self.initialize()
        return await self._marketplace_service.list_extensions()

    async def install_extension(
        self,
        extension_id: str,
        user_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Install an extension for a user."""
        if not self._initialized:
            await self.initialize()
        manager = ExtensionManager(self._session_factory, self._adapters)
        await manager.install(extension_id, user_id, config)

    async def uninstall_extension(self, extension_id: str, user_id: str) -> None:
        """Uninstall an extension for a user."""
        if not self._initialized:
            await self.initialize()
        manager = ExtensionManager(self._session_factory, self._adapters)
        await manager.uninstall(extension_id, user_id)

    async def list_user_extensions(self, user_id: str) -> List[Dict[str, Any]]:
        """List extensions installed for a user."""
        if not self._initialized:
            await self.initialize()
        manager = ExtensionManager(self._session_factory, self._adapters)
        return await manager.list_user_extensions(user_id)

    async def list_extension_tools(self, extension_id: str) -> List[Dict[str, Any]]:
        """List tools provided by an extension."""
        if not self._initialized:
            await self.initialize()
        registry = ToolRegistry(self._session_factory)
        tools = await registry.list_tools(extension_id=extension_id)
        if tools:
            return tools

        extension = self._extension_index.get(extension_id)
        if extension is None:
            raise ValueError(f"Extension not found: {extension_id}")

        adapter = self._create_adapter(extension_id, {})
        descriptors = await adapter.list_tools()
        return [
            {
                "id": descriptor.id,
                "name": descriptor.name,
                "display_name": getattr(descriptor, "display_name", None),
                "description": descriptor.description,
                "extension_id": extension_id,
                "extension_name": extension.name,
                "tool_type": extension.tool_type,
                "input_schema": descriptor.input_schema,
                "output_schema": descriptor.output_schema,
                "mcp_tool_name": getattr(descriptor, "mcp_tool_name", None),
                "risk_level": descriptor.risk_level,
                "side_effect": descriptor.side_effect,
                "requires_confirmation": descriptor.requires_confirmation,
                "allowed_intents": descriptor.allowed_intents,
                "domains": descriptor.domains,
                "requires_auth_scope": descriptor.requires_auth_scope,
                "max_calls_per_run": descriptor.max_calls_per_run,
                "timeout_ms": descriptor.timeout_ms,
                "returns_sensitive_data": descriptor.returns_sensitive_data,
                "audit_payload_level": descriptor.audit_payload_level,
                "openai_schema": descriptor.to_openai_schema(),
            }
            for descriptor in descriptors
        ]

    async def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas in OpenAI function-calling format."""
        if not self._initialized:
            await self.initialize()
        registry = ToolRegistry(self._session_factory)
        tools = await registry.list_tools()
        schemas = []
        for tool in tools:
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool["id"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                },
            })
        return schemas

    async def get_tool_catalog_entries(self, tool_ids: List[str]) -> List[Dict[str, Any]]:
        if not self._initialized:
            await self.initialize()
        registry = ToolRegistry(self._session_factory)
        return await registry.get_tools(tool_ids)

    async def test_extension_connection(
        self,
        extension_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        return self._validate_extension_config(extension_id, config)

    async def close(self) -> None:
        """Cleanup resources."""
        if self._engine:
            await close_db(self._engine)


def create_router():
    """Factory: create FastAPI router for the marketplace API."""
    from plugin_marketplace.api.routes import create_router as _create
    return _create()


# Singleton instance for backend/main.py startup wiring
plugin_marketplace_api: Optional[MarketplaceAPI] = None


async def init_plugin_marketplace(database_url: str) -> MarketplaceAPI:
    """Initialize the singleton marketplace API."""
    global plugin_marketplace_api
    engine, session_factory = create_engine_and_session(database_url)
    await init_db(engine)
    api = MarketplaceAPI(database_url=database_url, session_factory=session_factory)
    await api.initialize()
    plugin_marketplace_api = api
    return api
