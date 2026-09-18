"""
plugin_marketplace.core.executor
Tool executor implementation - dispatches to the right adapter.
"""

import time
import json
from typing import Dict, Any, Optional

from plugin_marketplace.interfaces import ToolExecutor
from plugin_marketplace.core.registry import ToolRegistry


class ToolExecutorImpl(ToolExecutor):
    """
    Default tool executor that dispatches to registered adapters.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        adapters: Dict[str, Any],  # extension_id -> adapter instance
        events: Optional[Any] = None,
    ):
        self.registry = registry
        self.adapters = adapters
        self.events = events

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute a tool by name, dispatching to the appropriate adapter.
        """
        # Parse extension_id/tool_name
        parts = tool_name.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid tool name format: {tool_name}. Expected 'extension_id/tool_name'")
        extension_id, tool_short_name = parts

        # Find the adapter
        adapter = self.adapters.get(extension_id)
        if not adapter:
            raise ValueError(f"No adapter found for extension: {extension_id}")

        # Execute
        start = time.time()
        error = None
        result = None
        try:
            result = await adapter.execute(tool_short_name, arguments)
        except Exception as e:
            error = str(e)
            raise

        duration_ms = int((time.time() - start) * 1000)

        # Fire event
        if self.events:
            try:
                await self.events.on_tool_executed(
                    tool_id=tool_name,
                    arguments=arguments,
                    result=result or "",
                    error=error,
                    duration_ms=duration_ms,
                )
            except Exception:
                pass  # Don't let event errors affect execution

        return result
