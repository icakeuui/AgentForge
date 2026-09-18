"""
Builtin adapter for AgentForge plugin marketplace.
Provides document-aligned aliases such as echo_tool and python_executor.
"""

from __future__ import annotations

import asyncio
import ast
import html
import math
import json
import operator
import re
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from backend.services.sandbox_service import sandbox_service
from plugin_marketplace.adapters.base import BaseAdapter
from plugin_marketplace.interfaces import ToolDescriptor, ToolType


class EchoTool:
    """Echo tool - returns the input text."""

    aliases = ("echo", "echo_tool")
    description = "Echo back the input text"
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to echo back."}},
        "required": ["text"],
        "additionalProperties": False,
    }

    async def execute(self, arguments: dict) -> str:
        text = arguments.get("text", "")
        return json.dumps({"echo": text})


class PythonExecTool:
    """Python execution tool."""

    aliases = ("python_exec", "python_executor")
    description = "Execute Python code and return the result"
    input_schema = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Python code to execute."}},
        "required": ["code"],
        "additionalProperties": False,
    }

    async def execute(self, arguments: dict) -> str:
        code = arguments.get("code", "")
        result = sandbox_service.execute_python(code, {})
        return json.dumps(result.get("observation"))


class PythonAddTool:
    """Add two integers inside the sandbox."""

    aliases = ("python_add_tool",)
    description = "Add two integers and return the sum"
    input_schema = {
        "type": "object",
        "properties": {
            "a": {"type": "integer", "description": "First integer."},
            "b": {"type": "integer", "description": "Second integer."},
        },
        "required": ["a", "b"],
        "additionalProperties": False,
    }

    async def execute(self, arguments: dict) -> str:
        code = "result = {'result': input_data['a'] + input_data['b']}"
        result = sandbox_service.execute_python(code, {"a": arguments.get("a"), "b": arguments.get("b")})
        return json.dumps(result.get("observation"))


class CalculateTool:
    """Safely evaluate a basic arithmetic expression."""

    aliases = ("calculate", "caculate")
    description = "Safely calculate a basic arithmetic expression. Supports +, -, *, /, //, %, ** and parentheses."
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression to calculate, for example '(12 + 8) / 5'.",
            }
        },
        "required": ["expression"],
        "additionalProperties": False,
    }

    _binary_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    _unary_ops = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    async def execute(self, arguments: dict) -> str:
        expression = str(arguments.get("expression", "")).strip()
        if not expression:
            raise ValueError("expression is required")
        if len(expression) > 200:
            raise ValueError("expression is too long")
        parsed = ast.parse(expression, mode="eval")
        result = self._eval_node(parsed.body)
        if isinstance(result, float) and not math.isfinite(result):
            raise ValueError("calculation result is not finite")
        return json.dumps({"expression": expression, "result": result}, ensure_ascii=False)

    @classmethod
    def _eval_node(cls, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            operation = cls._binary_ops.get(op_type)
            if operation is None:
                raise ValueError("unsupported operator")
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            if op_type is ast.Pow and abs(right) > 10:
                raise ValueError("exponent is too large")
            return operation(left, right)
        if isinstance(node, ast.UnaryOp):
            operation = cls._unary_ops.get(type(node.op))
            if operation is None:
                raise ValueError("unsupported unary operator")
            return operation(cls._eval_node(node.operand))
        raise ValueError("only arithmetic expressions are supported")


class WebSearchTool:
    """Search the public web and return lightweight result snippets."""

    aliases = ("websearch", "web_search")
    description = "Search the web for current public information and return result titles, links, and snippets."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return, from 1 to 5.",
                "minimum": 1,
                "maximum": 5,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    async def execute(self, arguments: dict) -> str:
        query = str(arguments.get("query", "")).strip()
        if not query:
            raise ValueError("query is required")
        limit = int(arguments.get("limit") or 5)
        limit = min(max(limit, 1), 5)
        results = await asyncio.to_thread(self._search_duckduckgo, query, limit)
        return json.dumps({"query": query, "results": results}, ensure_ascii=False)

    @staticmethod
    def _search_duckduckgo(query: str, limit: int) -> list[dict[str, str]]:
        url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AgentForgeTool/1.0)",
            },
        )
        with urlopen(request, timeout=8) as response:
            raw_html = response.read().decode("utf-8", errors="ignore")

        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="(?P<link>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
            re.DOTALL,
        )
        results: list[dict[str, str]] = []
        for match in pattern.finditer(raw_html):
            title = WebSearchTool._clean_html(match.group("title"))
            link = html.unescape(match.group("link"))
            snippet = WebSearchTool._clean_html(match.group("snippet"))
            if title and link:
                results.append({"title": title, "url": link, "snippet": snippet})
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _clean_html(value: str) -> str:
        text = re.sub(r"<.*?>", "", value)
        return html.unescape(text).strip()


class BuiltinAdapter(BaseAdapter):
    """
    Builtin tool adapter for AgentForge.
    Provides echo and python_exec tools.
    """

    def __init__(self, extension_id: str = "builtin", config: dict | None = None):
        super().__init__(extension_id, config or {})
        self._tools: dict[str, Any] = {
            "echo": EchoTool(),
            "python_exec": PythonExecTool(),
            "python_add_tool": PythonAddTool(),
            "calculate": CalculateTool(),
            "websearch": WebSearchTool(),
        }

    RISK_PROFILES: dict[str, dict[str, Any]] = {
        "echo": {
            "risk_level": "low",
            "side_effect": "none",
            "requires_confirmation": False,
            "allowed_intents": ["DIRECT_CHAT", "TOOL_OPTIONAL", "TOOL_REQUIRED"],
            "domains": ["utility"],
            "max_calls_per_run": 2,
        },
        "echo_tool": {
            "risk_level": "low",
            "side_effect": "none",
            "requires_confirmation": False,
            "allowed_intents": ["DIRECT_CHAT", "TOOL_OPTIONAL", "TOOL_REQUIRED"],
            "domains": ["utility"],
            "max_calls_per_run": 2,
        },
        "python_exec": {
            "risk_level": "high",
            "side_effect": "write",
            "requires_confirmation": True,
            "allowed_intents": ["HIGH_RISK_TOOL", "TOOL_REQUIRED"],
            "domains": ["python"],
            "max_calls_per_run": 1,
        },
        "python_executor": {
            "risk_level": "high",
            "side_effect": "write",
            "requires_confirmation": True,
            "allowed_intents": ["HIGH_RISK_TOOL", "TOOL_REQUIRED"],
            "domains": ["python"],
            "max_calls_per_run": 1,
        },
        "python_add_tool": {
            "risk_level": "low",
            "side_effect": "none",
            "requires_confirmation": False,
            "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
            "domains": ["calculator", "python"],
            "max_calls_per_run": 4,
        },
        "calculate": {
            "risk_level": "low",
            "side_effect": "none",
            "requires_confirmation": False,
            "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
            "domains": ["calculator", "utility"],
            "max_calls_per_run": 4,
        },
        "caculate": {
            "risk_level": "low",
            "side_effect": "none",
            "requires_confirmation": False,
            "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
            "domains": ["calculator", "utility"],
            "max_calls_per_run": 4,
        },
        "websearch": {
            "risk_level": "medium",
            "side_effect": "external_read",
            "requires_confirmation": False,
            "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
            "domains": ["web_search"],
            "max_calls_per_run": 2,
        },
        "web_search": {
            "risk_level": "medium",
            "side_effect": "external_read",
            "requires_confirmation": False,
            "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
            "domains": ["web_search"],
            "max_calls_per_run": 2,
        },
    }

    @property
    def tool_type(self) -> ToolType:
        return "builtin"

    async def discover_tools(self) -> list[Any]:
        return await self.list_tools()

    async def execute(self, tool_name: str, arguments: dict) -> str:
        tool = self._resolve_tool(tool_name)
        if not tool:
            raise ValueError(f"Unknown builtin tool: {tool_name}")
        return await tool.execute(arguments)

    async def list_tools(self) -> list[ToolDescriptor]:
        descriptors = []
        for tool in self._tools.values():
            for alias in tool.aliases:
                risk_profile = self.RISK_PROFILES.get(alias, {})
                descriptors.append(ToolDescriptor(
                    extension_id_value=self.extension_id,
                    name_value=alias,
                    description_value=tool.description,
                    tool_type_value="builtin",
                    input_schema_value=tool.input_schema,
                    **risk_profile,
                ))
        return descriptors

    async def get_tool(self, tool_name: str) -> ToolDescriptor | None:
        tool = self._resolve_tool(tool_name)
        if tool is None:
            return None
        tools = await self.list_tools()
        return next((t for t in tools if t.name == tool_name), None)

    async def install(self) -> None:
        pass  # Builtin tools need no installation

    async def uninstall(self) -> None:
        pass  # Builtin tools need no uninstallation

    async def health_check(self) -> bool:
        return True  # Always healthy

    def _resolve_tool(self, tool_name: str) -> Any | None:
        for tool in self._tools.values():
            if tool_name in tool.aliases:
                return tool
        return None
