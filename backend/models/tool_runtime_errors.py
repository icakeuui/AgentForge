from enum import Enum
from typing import Optional

class ToolRuntimeErrorCode(str, Enum):
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    SANDBOX_ERROR = "SANDBOX_ERROR"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    INTERNAL_RUNTIME_ERROR = "INTERNAL_RUNTIME_ERROR"
    TOOL_REGISTRATION_ERROR = "TOOL_REGISTRATION_ERROR"

class ToolRuntimeError(Exception):
    """Base exception for all tool runtime errors."""
    def __init__(self, code: ToolRuntimeErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(message)

class ToolRegistrationError(ToolRuntimeError):
    """Raised when a tool registration fails."""
    def __init__(self, message: str):
        super().__init__(ToolRuntimeErrorCode.TOOL_REGISTRATION_ERROR, message)
