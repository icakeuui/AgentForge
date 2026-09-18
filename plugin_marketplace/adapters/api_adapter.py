from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import httpx

from plugin_marketplace.adapters.base import BaseAdapter
from plugin_marketplace.exceptions import ToolExecuteError
from plugin_marketplace.interfaces import ToolDescriptor, ToolType


class APIAdapter(BaseAdapter):
    def __init__(self, extension, user_config: Dict[str, Any] | None = None):
        super().__init__(extension=extension, user_config=user_config)

    @property
    def tool_type(self) -> ToolType:
        return ToolType.API

    async def discover_tools(self) -> List[ToolDescriptor]:
        manifest_tools = self._tools_from_manifest()
        if manifest_tools:
            return manifest_tools

        spec = await self._load_openapi_spec()
        tools: List[ToolDescriptor] = []
        for path, operations in spec.get("paths", {}).items():
            for method, operation in operations.items():
                operation_id = operation.get("operationId") or f"{method}_{path.strip('/').replace('/', '_')}"
                description = operation.get("summary") or operation.get("description") or operation_id
                parameters = {"type": "object", "properties": {}, "required": []}
                for parameter in operation.get("parameters", []):
                    name = parameter["name"]
                    parameters["properties"][name] = parameter.get("schema", {"type": "string"})
                    if parameter.get("required"):
                        parameters["required"].append(name)
                request_body = (
                    operation.get("requestBody", {})
                    .get("content", {})
                    .get("application/json", {})
                    .get("schema")
                )
                if request_body:
                    parameters["properties"]["body"] = request_body
                tools.append(
                    ToolDescriptor(
                        extension_id_value=self.extension.id,
                        name_value=operation_id,
                        description_value=description,
                        tool_type_value=ToolType.API,
                        input_schema_value=parameters,
                        display_name=operation.get("summary"),
                    )
                )
        return tools

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        manifest_tool = self._manifest_tool(tool_name)
        if manifest_tool:
            return await self._execute_manifest_tool(manifest_tool, arguments)

        spec = await self._load_openapi_spec()
        base_url = (spec.get("servers") or [{"url": self.user_config.get("base_url", "")}])[0]["url"]
        method, path, operation = self._resolve_operation(spec, tool_name)
        headers = self._build_headers()
        query: Dict[str, Any] = {}
        body = arguments.get("body")

        for parameter in operation.get("parameters", []):
            value = arguments.get(parameter["name"])
            if value is None:
                continue
            if parameter.get("in") == "query":
                query[parameter["name"]] = value
            elif parameter.get("in") == "path":
                path = path.replace(f"{{{parameter['name']}}}", str(value))
            elif parameter.get("in") == "header":
                headers[parameter["name"]] = str(value)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method.upper(),
                f"{base_url.rstrip('/')}{path}",
                params=query,
                json=body,
                headers=headers,
            )
        response.raise_for_status()
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {"text": response.text}
        return json.dumps(payload, ensure_ascii=False, default=str)

    async def install(self) -> None:
        return None

    async def uninstall(self) -> None:
        return None

    async def health_check(self) -> bool:
        return True

    async def _load_openapi_spec(self) -> Dict[str, Any]:
        manifest = self.extension.manifest or {}
        openapi = manifest.get("openapi", {})
        if openapi.get("spec"):
            return openapi["spec"]
        url = openapi.get("url")
        if not url:
            raise ToolExecuteError(f"Extension {self.extension.id} has no OpenAPI spec configured.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
        response.raise_for_status()
        return response.json()

    def _resolve_operation(self, spec: Dict[str, Any], tool_name: str) -> Tuple[str, str, Dict[str, Any]]:
        for path, operations in spec.get("paths", {}).items():
            for method, operation in operations.items():
                operation_id = operation.get("operationId") or f"{method}_{path.strip('/').replace('/', '_')}"
                if operation_id == tool_name:
                    return method, path, operation
        raise ToolExecuteError(f"API tool {tool_name} not found for extension {self.extension.id}.")

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        openapi = (self.extension.manifest or {}).get("openapi", {})
        if self.user_config.get("authorization"):
            headers["Authorization"] = self.user_config["authorization"]
        elif self.user_config.get("api_key"):
            header_name = openapi.get("header_name")
            if header_name:
                headers[header_name] = str(self.user_config["api_key"])
            else:
                headers["Authorization"] = f"Bearer {self.user_config['api_key']}"
        return headers

    def _tools_from_manifest(self) -> List[ToolDescriptor]:
        manifest = self.extension.manifest or {}
        manifest_tools = manifest.get("tools", [])
        return [
            ToolDescriptor(
                extension_id_value=self.extension.id,
                name_value=item["name"],
                description_value=item.get("description", item["name"]),
                tool_type_value=ToolType.API,
                input_schema_value=item.get("input_schema") or {"type": "object", "properties": {}},
                display_name=item.get("display_name"),
            )
            for item in manifest_tools
        ]

    def _manifest_tool(self, tool_name: str) -> Dict[str, Any] | None:
        manifest = self.extension.manifest or {}
        for item in manifest.get("tools", []):
            if item.get("name") == tool_name:
                return item
        return None

    async def _execute_manifest_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> str:
        manifest = self.extension.manifest or {}
        openapi = manifest.get("openapi", {})
        base_url = self.user_config.get("base_url") or openapi.get("base_url")
        if not base_url:
            raise ToolExecuteError(f"Extension {self.extension.id} has no API base URL configured.")

        path = tool.get("path") or "/search"
        method = (tool.get("method") or "get").upper()
        headers = self._build_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                f"{base_url.rstrip('/')}{path}",
                params=arguments,
                headers=headers,
            )
        response.raise_for_status()
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {"text": response.text}
        return json.dumps(payload, ensure_ascii=False, default=str)
