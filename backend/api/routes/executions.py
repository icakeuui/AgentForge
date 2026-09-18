import uuid
from fastapi import APIRouter, Depends
from backend.models.schemas import BaseResponse
from backend.services.execution_log_service import execution_log_service
from backend.services.execution_cancellation_service import execution_cancellation_service
from backend.api.dependencies import get_current_user
from backend.core.logging import logger
from backend.core.exceptions import NotFoundException
from backend.models.schemas import AuthContext
from backend.models.constants import TerminationReason
from backend.services.authorization_service import authorization_service

router = APIRouter(prefix="/executions", tags=["Executions"])

STOPPED_BY_USER_MESSAGE = "已停止：用户主动停止了当前模型行为。"

@router.get("/{execution_id}", response_model=BaseResponse[dict])
async def get_execution(
    execution_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_user)
):
    await authorization_service.ensure_execution_record_ownership(auth, execution_id)
    result = await execution_log_service.get_execution_replay(execution_id, team_id=uuid.UUID(auth.team_id))
    if result is None:
        raise NotFoundException(f"Execution with ID {execution_id} not found or access denied")
    logger.bind(
        resource_type="execution_record",
        resource_id=str(execution_id),
    ).info(f"resource access log: read execution record {execution_id}")
    return BaseResponse.success(data=result, message="OK")


@router.post("/{execution_id}/stop", response_model=BaseResponse[dict])
async def stop_execution(
    execution_id: uuid.UUID,
    auth: AuthContext = Depends(get_current_user)
):
    await authorization_service.ensure_execution_record_ownership(auth, execution_id)
    task_cancelled = execution_cancellation_service.request_cancel(execution_id)
    log_updated = await execution_log_service.terminate_if_active(
        execution_id,
        final_answer=STOPPED_BY_USER_MESSAGE,
        termination_reason=TerminationReason.USER_STOPPED.value,
        team_id=uuid.UUID(auth.team_id),
    )
    logger.bind(
        resource_type="execution_record",
        resource_id=str(execution_id),
    ).info(f"resource access log: stop execution record {execution_id}")
    return BaseResponse.success(
        data={
            "execution_id": str(execution_id),
            "status": "TERMINATED",
            "stopped": task_cancelled or log_updated,
            "message": STOPPED_BY_USER_MESSAGE,
        },
        message="OK",
    )
