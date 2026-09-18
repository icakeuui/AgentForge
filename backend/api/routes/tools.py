from backend.models.tool import ToolResponse

from typing import Any, Dict
from fastapi import APIRouter, Body, Depends
from backend.core.tool_runtime import ToolExecutor
from backend.core.logging import get_request_id, logger
from backend.api.dependencies import get_current_user
from backend.models.schemas import AuthContext

router = APIRouter()

@router.post("/tools/execute", response_model=ToolResponse)
async def execute_tool(
    tool_name: str = Body(..., embed=True),
    input_data: Dict[str, Any] = Body(..., embed=True),
    auth: AuthContext = Depends(get_current_user)
) -> ToolResponse:
    """
    Minimum Tool Runtime API endpoint.
    Executes a registered tool and returns the structured response.
    """
    request_id = get_request_id()
    logger.bind(resource_type="tool_binding", resource_id=tool_name).info(
        f"execution trace log: tool execute request tool={tool_name}"
    )
    
    # Delegate to the ToolExecutor for the full execution flow
    # (including schema validation, logging, and error isolation)
    return ToolExecutor.execute(
        name=tool_name, 
        input_data=input_data, 
        request_id=request_id
    )
