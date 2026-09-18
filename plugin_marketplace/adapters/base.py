"""
plugin_marketplace.adapters.base
Base adapter class for all tool adapters.
"""

from abc import ABC, abstractmethod
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from plugin_marketplace.interfaces import ToolType


class BaseAdapter(ABC):
    """Base adapter class for all tool adapters."""

    def __init__(
        self,
        extension_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        extension: Any = None,
        user_config: Optional[Dict[str, Any]] = None,
    ):
        if extension is None:
            extension = SimpleNamespace(id=extension_id, manifest={})
        self.extension = extension
        self.extension_id = extension.id
        self.config = config or {}
        self.user_config = user_config or self.config

    @property
    @abstractmethod
    def tool_type(self) -> ToolType:
        """Tool type."""
        raise NotImplementedError

    @abstractmethod
    async def discover_tools(self) -> List[Any]:
        """Discover tools exposed by the adapter."""
        raise NotImplementedError

    async def list_tools(self) -> List[Any]:
        """Default alias used by lifecycle code."""
        return await self.discover_tools()

    @abstractmethod
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool exposed by the adapter."""
        raise NotImplementedError

    @abstractmethod
    async def install(self) -> None:
        """Install or initialize adapter runtime."""
        raise NotImplementedError

    @abstractmethod
    async def uninstall(self) -> None:
        """Uninstall or teardown adapter runtime."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Return adapter health."""
        raise NotImplementedError
