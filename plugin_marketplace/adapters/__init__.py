"""
plugin_marketplace.adapters
Tool adapters: BuiltinAdapter, MCPAdapter, APIAdapter.
"""

from plugin_marketplace.adapters.base import BaseAdapter
from plugin_marketplace.adapters.builtin_adapter import BuiltinAdapter
from plugin_marketplace.adapters.mcp_adapter import MCPAdapter
from plugin_marketplace.adapters.api_adapter import APIAdapter

__all__ = ["BaseAdapter", "BuiltinAdapter", "MCPAdapter", "APIAdapter"]
