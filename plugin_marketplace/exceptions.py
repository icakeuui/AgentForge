class PluginMarketplaceError(Exception):
    """Base exception for the plugin marketplace."""


class ExtensionNotFoundError(PluginMarketplaceError):
    """Raised when an extension cannot be found."""


class ExtensionInstallError(PluginMarketplaceError):
    """Raised when an extension cannot be installed."""


class ToolNotFoundError(PluginMarketplaceError):
    """Raised when a tool cannot be found."""


class ToolExecuteError(PluginMarketplaceError):
    """Raised when a tool execution fails."""


class ToolBindingValidationError(PluginMarketplaceError):
    """Raised when requested tool bindings cannot be resolved."""

    def __init__(
        self,
        message: str,
        *,
        missing_tool_ids: list[str] | None = None,
        resolved_tool_ids: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.missing_tool_ids = missing_tool_ids or []
        self.resolved_tool_ids = resolved_tool_ids or []


class MCPConnectionError(PluginMarketplaceError):
    """Raised when an MCP endpoint cannot be reached."""


class ManifestValidationError(PluginMarketplaceError):
    """Raised when a manifest is invalid."""
