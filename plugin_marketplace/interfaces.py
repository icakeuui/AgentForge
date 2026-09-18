from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ToolType(str, Enum):
    MCP = "mcp"
    BUILTIN = "builtin"
    API = "api"


class ToolInfo(ABC):
    """Abstract contract describing a marketplace tool."""

    @property
    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def extension_id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def tool_type(self) -> ToolType:
        raise NotImplementedError

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        raise NotImplementedError

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {"type": "object"}


@dataclass(slots=True)
class ToolDescriptor(ToolInfo):
    extension_id_value: str
    name_value: str
    description_value: str
    tool_type_value: ToolType
    input_schema_value: Dict[str, Any] = field(default_factory=dict)
    output_schema_value: Dict[str, Any] = field(default_factory=lambda: {"type": "object"})
    display_name: Optional[str] = None
    mcp_tool_name: Optional[str] = None
    risk_level: str = "medium"
    side_effect: str = "read"
    requires_confirmation: bool = False
    allowed_intents: list[str] = field(default_factory=lambda: ["TOOL_REQUIRED", "TOOL_OPTIONAL"])
    domains: list[str] = field(default_factory=list)
    requires_auth_scope: list[str] = field(default_factory=list)
    max_calls_per_run: int = 2
    timeout_ms: int = 10000
    returns_sensitive_data: bool = False
    audit_payload_level: str = "summary"

    @property
    def id(self) -> str:
        return f"{self.extension_id_value}/{self.name_value}"

    @property
    def name(self) -> str:
        return self.name_value

    @property
    def description(self) -> str:
        return self.description_value

    @property
    def extension_id(self) -> str:
        return self.extension_id_value

    @property
    def tool_type(self) -> ToolType:
        return self.tool_type_value

    @property
    def input_schema(self) -> Dict[str, Any]:
        return self.input_schema_value

    @property
    def output_schema(self) -> Dict[str, Any]:
        return self.output_schema_value

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.id,
                "description": self.description,
                "parameters": self.input_schema or {"type": "object", "properties": {}},
            },
        }


class ToolExecutor(ABC):
    """Execution contract exposed to the host application."""

    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        raise NotImplementedError


class ExtensionEvents(ABC):
    """Optional lifecycle hooks."""

    async def on_extension_installed(self, extension_id: str, user_id: str) -> None:
        return None

    async def on_extension_uninstalled(self, extension_id: str, user_id: str) -> None:
        return None

    async def on_tool_executed(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        result: str,
        error: Optional[str] = None,
        duration_ms: int = 0,
    ) -> None:
        return None

    async def on_tool_error(self, tool_id: str, arguments: Dict[str, Any], error: str) -> None:
        return None
