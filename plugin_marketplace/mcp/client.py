from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

import httpx

from plugin_marketplace.exceptions import MCPConnectionError
from plugin_marketplace.mcp.protocol import MCPProtocol
from plugin_marketplace.mcp.server import MCPServer


class MCPClient:
    def __init__(
        self,
        transport: str,
        server: Optional[MCPServer] = None,
        url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.transport = transport
        self.server = server
        self.url = url
        self.timeout = timeout
        self.protocol = MCPProtocol()
        self._pending: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self._stdin_lock = asyncio.Lock()

    async def connect(self) -> None:
        if self.transport == "stdio":
            if not self.server or not self.server.process:
                raise MCPConnectionError("STDIO MCP client requires a running server.")
            self._reader_task = asyncio.create_task(self._read_loop())
            return
        if not self.url:
            raise MCPConnectionError("HTTP MCP client requires a URL.")

    async def list_tools(self) -> Dict[str, Any]:
        return await self.request("tools/list")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("tools/call", {"name": tool_name, "arguments": arguments})

    async def ping(self) -> Dict[str, Any]:
        return await self.request("ping")

    async def request(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = self.protocol.request(method, params)
        if self.transport == "http":
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.url, json=payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise MCPConnectionError(str(data["error"]))
            return data.get("result", {})

        if not self.server or not self.server.process or not self.server.process.stdin:
            raise MCPConnectionError("MCP STDIO server is not connected.")
        future = asyncio.get_running_loop().create_future()
        self._pending[payload["id"]] = future
        async with self._stdin_lock:
            self.server.process.stdin.write(json.dumps(payload).encode("utf-8") + b"\n")
            await self.server.process.stdin.drain()
        return await asyncio.wait_for(future, timeout=self.timeout)

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task

    async def _read_loop(self) -> None:
        assert self.server and self.server.process and self.server.process.stdout
        while True:
            line = await self.server.process.stdout.readline()
            if not line:
                break
            message = json.loads(line.decode("utf-8"))
            request_id = message.get("id")
            future = self._pending.pop(request_id, None)
            if not future:
                continue
            if "error" in message:
                future.set_exception(MCPConnectionError(str(message["error"])))
            else:
                future.set_result(message.get("result", {}))
