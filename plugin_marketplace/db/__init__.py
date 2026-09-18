"""
plugin_marketplace.db
Database models for the plugin marketplace.
"""

from plugin_marketplace.db.database import (
    Base,
    create_engine_and_session,
    init_db,
    close_db,
)
from plugin_marketplace.db.models import (
    Extension as PMExtension,
    Tool as PMTool,
    UserExtension as PMUserExtension,
    AgentToolBinding as PMAgentTool,
)

# Aliases for backwards compatibility
Extension = PMExtension
Tool = PMTool
UserExtension = PMUserExtension
AgentToolBinding = PMAgentTool

__all__ = [
    "Base",
    "create_engine_and_session",
    "init_db",
    "close_db",
    "PMExtension",
    "PMTool",
    "PMUserExtension",
    "PMAgentTool",
    "Extension",
    "Tool",
    "UserExtension",
    "AgentToolBinding",
]
