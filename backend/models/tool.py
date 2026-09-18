from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field, model_validator
from backend.models.tool_runtime_errors import ToolRuntimeErrorCode

class ToolDefinition(BaseModel):
    """
    Metadata for a tool.
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class BaseTool(ABC):
    """
    Abstract base class for all tools.
    Must implement business logic in execute().
    """
    def __init__(self, definition: ToolDefinition):
        self.definition = definition

    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pure business logic execution.
        Must return a dictionary.
        """
        pass

class ToolError(BaseModel):
    """
    Error structure for tool execution.
    """
    code: ToolRuntimeErrorCode
    message: str

class ToolSuccessResponse(BaseModel):
    ok: bool = Field(default=True, frozen=True)
    data: Dict[str, Any]

class ToolFailureResponse(BaseModel):
    ok: bool = Field(default=False, frozen=True)
    error: ToolError

ToolResponse = Union[ToolSuccessResponse, ToolFailureResponse]
