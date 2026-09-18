import json
from types import SimpleNamespace

import pytest

from plugin_marketplace.adapters.api_adapter import APIAdapter
from plugin_marketplace.adapters.builtin_adapter import BuiltinAdapter


@pytest.mark.asyncio
async def test_builtin_echo_executes():
    adapter = BuiltinAdapter("builtin", {})
    result = await adapter.execute("echo", {"text": "hello"})
    payload = json.loads(result)
    assert payload["echo"] == "hello"


@pytest.mark.asyncio
async def test_api_adapter_uses_inline_openapi_spec_and_executes(monkeypatch):
    extension = SimpleNamespace(
        id="weather",
        manifest={
            "openapi": {
                "spec": {
                    "servers": [{"url": "https://example.com"}],
                    "paths": {
                        "/forecast/{city}": {
                            "get": {
                                "operationId": "getForecast",
                                "summary": "Get forecast",
                                "parameters": [
                                    {"name": "city", "in": "path", "required": True, "schema": {"type": "string"}},
                                    {"name": "days", "in": "query", "required": False, "schema": {"type": "integer"}},
                                ],
                            }
                        }
                    },
                }
            }
        },
    )
    adapter = APIAdapter(extension, {"api_key": "secret"})

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"ok": True}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, params=None, json=None, headers=None):
            captured["method"] = method
            captured["url"] = url
            captured["params"] = params
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr("plugin_marketplace.adapters.api_adapter.httpx.AsyncClient", lambda timeout=30.0: FakeClient())

    tools = await adapter.discover_tools()
    assert len(tools) == 1
    assert tools[0].id == "weather/getForecast"

    result = await adapter.execute("getForecast", {"city": "shanghai", "days": 3})
    payload = json.loads(result)

    assert payload["ok"] is True
    assert captured["method"] == "GET"
    assert captured["url"] == "https://example.com/forecast/shanghai"
    assert captured["params"] == {"days": 3}
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_manifest_parser_normalizes_mcp_and_api_layouts():
    from plugin_marketplace.marketplace.manifest import ManifestParser

    parser = ManifestParser()

    github = parser.parse_manifest(
        {
            "id": "github",
            "name": "GitHub",
            "tool_type": "mcp",
            "categories": ["development"],
            "author": "GitHub",
            "homepage": "https://github.com",
            "popularity": 100,
            "is_official": True,
            "mcp": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "server-github"],
                "env_vars": {"GITHUB_TOKEN": ""},
            },
            "tools": [{"name": "search_repos"}],
        }
    )
    assert github["runtime"]["transport"] == "stdio"
    assert github["install"]["command"] == "npx"
    assert github["install"]["args"] == ["-y", "server-github"]
    assert github["categories"] == ["development"]
    assert github["manifest"]["runtime"]["env_vars"] == ["GITHUB_TOKEN"]

    brave = parser.parse_manifest(
        {
            "id": "brave_search",
            "name": "Brave Search",
            "tool_type": "api",
            "api": {
                "base_url": "https://api.search.brave.com",
                "auth_type": "api_key",
                "header_name": "X-Subscription-Token",
            },
            "tools": [{"name": "web_search", "input_schema": {"type": "object"}}],
        }
    )
    assert brave["openapi"]["base_url"] == "https://api.search.brave.com"
    assert brave["openapi"]["header_name"] == "X-Subscription-Token"
