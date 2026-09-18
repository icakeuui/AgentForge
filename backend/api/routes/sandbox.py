from fastapi import APIRouter, Depends
from backend.models.schemas import SandboxRequest, SandboxResponse, BaseResponse, AuthContext
from backend.services.sandbox_service import sandbox_service
from backend.core.logging import logger
from backend.api.dependencies import get_current_user

router = APIRouter(prefix="/sandbox")

@router.post("/execute", response_model=BaseResponse[SandboxResponse])
async def execute_sandbox(
    request: SandboxRequest,
    auth: AuthContext = Depends(get_current_user)
):
    """
    Execute Python code in a secure sandbox.
    Direct API exposure for testing and standalone tool usage.
    """
    logger.bind(resource_type="execution_artifact", resource_id="sandbox").info(
        "execution trace log: sandbox execution API called."
    )
    
    # Delegate to sandbox service
    result = sandbox_service.execute_python(request.code, request.input_data)
    
    # Map the result to SandboxResponse schema
    sandbox_response = SandboxResponse(observation=result["observation"])
    
    # Wrap in unified BaseResponse
    return BaseResponse.success(data=sandbox_response)
