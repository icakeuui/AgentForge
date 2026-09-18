from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from plugin_marketplace.adapters.base import BaseAdapter
from plugin_marketplace.interfaces import ToolDescriptor, ToolType
from plugin_marketplace.mcp.client import MCPClient
from plugin_marketplace.mcp.server import MCPServer


class MCPAdapter(BaseAdapter):
    def __init__(self, extension, user_config: Dict[str, Any] | None = None):
        super().__init__(extension=extension, user_config=user_config)
        self.server: Optional[MCPServer] = None
        self.client: Optional[MCPClient] = None

    @property
    def tool_type(self) -> ToolType:
        return ToolType.MCP

    async def discover_tools(self) -> List[ToolDescriptor]:
        if self.client:
            try:
                payload = await self.client.list_tools()
                tools = payload.get("tools", payload)
                if isinstance(tools, list):
                    return [self._tool_from_remote(item) for item in tools]
            except Exception:
                pass
        return self._tool_from_manifest()

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        await self._ensure_client()
        assert self.client is not None
        payload = await self.client.call_tool(tool_name, arguments)
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def install(self) -> None:
        runtime = self.extension.manifest.get("runtime", {}) if self.extension.manifest else {}
        install = self.extension.manifest.get("install", {}) if self.extension.manifest else {}
        transport = runtime.get("transport", self.extension.mcp_transport or "stdio")
        if transport == "stdio":
            env_names = runtime.get("env_vars", [])
            env_vars = {name: str(self.user_config.get(name, "")) for name in env_names if self.user_config.get(name) is not None}
            args = list(install.get("args") or self.extension.mcp_args or [])
            if self.extension.id == "filesystem":
                root_path = self.user_config.get("root_path")
                if root_path:
                    args.append(str(root_path))
            self.server = MCPServer(
                command=install.get("command") or self.extension.mcp_command or "python",
                args=args,
                env_vars=env_vars,
            )
            await self.server.start()
            self.client = MCPClient(transport="stdio", server=self.server)
        else:
            url = runtime.get("url") or self.extension.mcp_url or self.user_config.get("url")
            self.client = MCPClient(transport="http", url=url)
        await self.client.connect()

    async def uninstall(self) -> None:
        if self.client:
            try:
                await self.client.close()
            except Exception:
                pass
        if self.server:
            await self.server.stop()

    async def health_check(self) -> bool:
        if not self.client:
            return False
        try:
            await self.client.ping()
            return True
        except Exception:
            return False

    def runtime_state(self) -> Dict[str, Any]:
        return {
            "process_id": self.server.process.pid if self.server and self.server.process else None,
        }

    async def _ensure_client(self) -> None:
        if self.client:
            return
        await self.install()

    def _tool_from_remote(self, item: Dict[str, Any]) -> ToolDescriptor:
        return ToolDescriptor(
            extension_id_value=self.extension.id,
            name_value=item.get("name", ""),
            description_value=item.get("description", ""),
            tool_type_value=ToolType.MCP,
            input_schema_value=item.get("inputSchema") or item.get("input_schema") or {"type": "object", "properties": {}},
            output_schema_value=item.get("outputSchema") or item.get("output_schema") or {"type": "object"},
            display_name=item.get("title"),
            mcp_tool_name=item.get("name"),
        )

    def _tool_from_manifest(self) -> List[ToolDescriptor]:
        manifest_tools = self.extension.manifest.get("tools", []) if self.extension.manifest else []
        return [
            ToolDescriptor(
                extension_id_value=self.extension.id,
                name_value=item["name"],
                description_value=item.get("description", item["name"]),
                tool_type_value=ToolType.MCP,
                input_schema_value=item.get("input_schema") or {"type": "object", "properties": {}},
                mcp_tool_name=item.get("mcp_tool_name") or item["name"],
            )
            for item in manifest_tools
        ]
