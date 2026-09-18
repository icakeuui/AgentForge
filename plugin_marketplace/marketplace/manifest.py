from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from plugin_marketplace.exceptions import ManifestValidationError
from plugin_marketplace.interfaces import ToolType


class ManifestParser:
    """Normalizes manifest files into a consistent dictionary shape."""

    def parse_file(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        manifest = self.parse_manifest(raw)
        manifest["manifest_path"] = str(path)
        return manifest

    def parse_manifest(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        if not raw.get("id"):
            raise ManifestValidationError("Manifest is missing 'id'.")
        if not raw.get("name"):
            raise ManifestValidationError(f"Manifest {raw['id']} is missing 'name'.")

        tool_type = raw.get("tool_type") or ToolType.MCP.value
        if tool_type not in {item.value for item in ToolType}:
            raise ManifestValidationError(f"Unsupported tool_type: {tool_type}")

        marketplace = {
            "categories": raw.get("categories", raw.get("marketplace", {}).get("categories", [])),
            "author": raw.get("author", raw.get("marketplace", {}).get("author")),
            "homepage": raw.get("homepage", raw.get("marketplace", {}).get("homepage")),
            "popularity": raw.get("popularity", raw.get("marketplace", {}).get("popularity", 0)),
            "is_official": raw.get("is_official", raw.get("marketplace", {}).get("is_official", False)),
        }

        if tool_type == ToolType.MCP.value:
            mcp_config = raw.get("mcp", {})
            runtime = {
                "transport": mcp_config.get("transport", raw.get("runtime", {}).get("transport", "stdio")),
                "url": mcp_config.get("url", raw.get("runtime", {}).get("url")),
                "env_vars": list((mcp_config.get("env_vars") or raw.get("runtime", {}).get("env_vars") or {}).keys())
                if isinstance(mcp_config.get("env_vars"), dict)
                else mcp_config.get("env_vars", raw.get("runtime", {}).get("env_vars", [])),
            }
            install = {
                "command": mcp_config.get("command", raw.get("install", {}).get("command")),
                "args": mcp_config.get("args", raw.get("install", {}).get("args", [])),
                "uninstall_command": raw.get("install", {}).get("uninstall_command"),
            }
            openapi = raw.get("openapi", {})
        elif tool_type == ToolType.API.value:
            api_config = raw.get("api", {})
            runtime = raw.get("runtime", {})
            install = raw.get("install", {})
            openapi = raw.get("openapi", {})
            if api_config:
                openapi = {
                    **openapi,
                    "base_url": api_config.get("base_url", openapi.get("base_url")),
                    "auth_type": api_config.get("auth_type", openapi.get("auth_type")),
                    "header_name": api_config.get("header_name", openapi.get("header_name")),
                    "spec": openapi.get("spec"),
                    "url": openapi.get("url"),
                }
        else:
            runtime = raw.get("runtime", {})
            install = raw.get("install", {})
            openapi = raw.get("openapi", {})

        normalized_manifest = {
            "id": raw["id"],
            "name": raw["name"],
            "description": raw.get("description", ""),
            "icon_url": raw.get("icon") or raw.get("icon_url"),
            "tool_type": tool_type,
            "tools": raw.get("tools", []),
            "install": install,
            "runtime": runtime,
            "config": raw.get("config", []),
            "marketplace": marketplace,
            "openapi": openapi,
            "builtin_tools": raw.get("builtin_tools", []),
        }

        manifest = {
            "id": raw["id"],
            "name": raw["name"],
            "description": raw.get("description", ""),
            "icon_url": raw.get("icon") or raw.get("icon_url"),
            "tool_type": tool_type,
            "tools": raw.get("tools", []),
            "install": install,
            "runtime": runtime,
            "config": raw.get("config", []),
            "marketplace": marketplace,
            "categories": marketplace["categories"],
            "author": marketplace["author"],
            "homepage": marketplace["homepage"],
            "popularity": marketplace["popularity"],
            "is_official": marketplace["is_official"],
            "openapi": openapi,
            "builtin_tools": raw.get("builtin_tools", []),
            "manifest": normalized_manifest,
        }
        return manifest

    def load_directory(self, directory: Path) -> List[Dict[str, Any]]:
        manifests: List[Dict[str, Any]] = []
        for path in sorted(directory.glob("*.yaml")):
            manifests.append(self.parse_file(path))
        return manifests

    @staticmethod
    def builtin_manifest() -> Dict[str, Any]:
        return {
            "id": "builtin",
            "name": "Built-in Tools",
            "description": "Local built-in tools bundled with AgentForge.",
            "icon_url": None,
            "tool_type": ToolType.BUILTIN.value,
            "tools": [],
            "install": {},
            "runtime": {},
            "config": [],
            "marketplace": {
                "categories": ["system", "utilities"],
                "tags": ["builtin", "python"],
                "popularity": 100,
                "author": "AgentForge",
                "homepage": None,
                "is_official": True,
            },
            "openapi": {},
            "builtin_tools": ["echo", "python_exec"],
            "manifest": {
                "id": "builtin",
                "name": "Built-in Tools",
                "tool_type": ToolType.BUILTIN.value,
                "builtin_tools": ["echo", "python_exec"],
            },
        }


def collect_manifest_ids(manifests: Iterable[Dict[str, Any]]) -> List[str]:
    return [manifest["id"] for manifest in manifests]
