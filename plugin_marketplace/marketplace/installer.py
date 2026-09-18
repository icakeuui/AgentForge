from __future__ import annotations

from typing import Any, Dict, List, Tuple

from plugin_marketplace.adapters.api_adapter import APIAdapter
from plugin_marketplace.adapters.builtin_adapter import BuiltinAdapter
from plugin_marketplace.adapters.mcp_adapter import MCPAdapter
from plugin_marketplace.db.models import Extension
from plugin_marketplace.interfaces import ToolDescriptor, ToolType


class ExtensionInstaller:
    """Creates adapters and runs install/uninstall flows."""

    def create_adapter(
        self,
        extension: Extension,
        user_config: Dict[str, Any] | None = None,
    ):
        effective_config = user_config or {}
        if extension.tool_type == ToolType.BUILTIN.value:
            return BuiltinAdapter(extension=extension, user_config=effective_config)
        if extension.tool_type == ToolType.API.value:
            return APIAdapter(extension=extension, user_config=effective_config)
        return MCPAdapter(extension=extension, user_config=effective_config)

    async def install(
        self,
        extension: Extension,
        user_config: Dict[str, Any] | None = None,
    ) -> Tuple[List[ToolDescriptor], Dict[str, Any]]:
        adapter = self.create_adapter(extension, user_config)
        await adapter.install()
        tools = await adapter.discover_tools()
        runtime = adapter.runtime_state()
        return tools, runtime

    async def uninstall(
        self,
        extension: Extension,
        user_config: Dict[str, Any] | None = None,
    ) -> None:
        adapter = self.create_adapter(extension, user_config)
        await adapter.uninstall()
