import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.exceptions import NotFoundException, QuotaException, ValidationException
from backend.core.logging import get_request_id, logger
from backend.core.rate_limiter import LimitStatus
from backend.models.constants import ExecutionState, ExecutionStatus, ResponseCode, TerminationReason
from backend.models.schemas import (
    AuthContext,
    BaseResponse,
    ExecuteAgentResponse,
    ExecutionErrorModel,
    PublicAgentSquareItem,
    PublicAgentProfile,
    PublicExecuteAgentRequest,
    TokenUsage,
)
from backend.services.agent_service import AgentService
from backend.services.competition_manager_service import competition_manager_service
from backend.services.execution_cancellation_service import execution_cancellation_service
from backend.services.execution_engine import execution_engine
from backend.services.execution_log_service import execution_log_service
from backend.services.published_agent_service import published_agent_service
from backend.services.public_conversation_attachment_service import public_conversation_attachment_service
from backend.services.knowledge_service import knowledge_service


router = APIRouter(prefix="/public/agents", tags=["Public Agents"])


@router.get("", response_model=BaseResponse[list[PublicAgentSquareItem]])
async def list_public_agents(db: AsyncSession = Depends(get_db)):
    records = await published_agent_service.list_active_records(db)
    items: list[PublicAgentSquareItem] = []
    for publication in records:
        agent = await AgentService.get_agent(db, publication.agent_id)
        if agent is None or not agent.is_available:
            continue
        items.append(
            PublicAgentSquareItem(
                slug=publication.slug,
                title=publication.title,
                description=publication.description,
                opening_statement=agent.opening_statement,
                avatar_url=agent.avatar_url,
            )
        )
    return BaseResponse.success(data=items, message="OK")


@router.get("/{slug}", response_model=BaseResponse[PublicAgentProfile])
async def get_public_agent(slug: str, db: AsyncSession = Depends(get_db)):
    publication = await published_agent_service.get_active_record_by_slug(db, slug)
    agent = await AgentService.get_agent(db, publication.agent_id)
    if agent is None or not agent.is_available:
        raise NotFoundException(f"Published agent with slug {slug} not found")
    profile = PublicAgentProfile(
        slug=publication.slug,
        title=publication.title,
        description=publication.description,
        opening_statement=agent.opening_statement,
        avatar_url=agent.avatar_url,
    )
    return BaseResponse.success(data=profile, message="OK")


@router.post("/{slug}/conversations", response_model=BaseResponse[dict])
async def create_public_conversation(slug: str, db: AsyncSession = Depends(get_db)):
    publication = await published_agent_service.get_active_record_by_slug(db, slug)
    agent = await AgentService.get_agent(db, publication.agent_id)
    if agent is None or not agent.is_available:
        raise NotFoundException(f"Published agent with slug {slug} not found")
    data = public_conversation_attachment_service.create(agent_id=str(publication.agent_id), slug=slug)
    return BaseResponse.success(data=data, message="OK")


@router.post("/{slug}/conversations/{conversation_id}/attachments", response_model=BaseResponse[dict])
async def upload_public_conversation_attachment(
    slug: str,
    conversation_id: uuid.UUID,
    file: UploadFile = File(...),
    x_public_conversation_token: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    publication = await published_agent_service.get_active_record_by_slug(db, slug)
    agent = await AgentService.get_agent(db, publication.agent_id)
    if agent is None or not agent.is_available:
        raise NotFoundException(f"Published agent with slug {slug} not found")
    chunks = bytearray()
    while chunk := await file.read(1024 * 1024):
        chunks.extend(chunk)
        if len(chunks) > knowledge_service.MAX_UPLOAD_BYTES:
            raise ValidationException("文件不能超过 100MB")
    data = public_conversation_attachment_service.add_file(
        conversation_id=conversation_id,
        token=x_public_conversation_token,
        agent_id=str(publication.agent_id),
        slug=slug,
        filename=file.filename or "未命名文件",
        content_type=file.content_type,
        data=bytes(chunks),
    )
    return BaseResponse.success(data=data, message="Uploaded successfully")


@router.get("/{slug}/executions/{execution_id}", response_model=BaseResponse[dict])
async def get_public_agent_execution(
    slug: str,
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    publication = await published_agent_service.get_active_record_by_slug(db, slug)
    replay = await execution_log_service.get_execution_replay(execution_id, team_id=publication.team_id)
    if replay is None or replay.get("agent_id") != str(publication.agent_id):
        raise NotFoundException(f"Execution with ID {execution_id} not found")
    return BaseResponse.success(data=replay, message="OK")


@router.post("/{slug}/execute", response_model=BaseResponse[ExecuteAgentResponse])
async def execute_public_agent(
    slug: str,
    request: PublicExecuteAgentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_public_conversation_token: str = Header(default=""),
):
    publication = await published_agent_service.get_active_record_by_slug(db, slug)
    agent = await AgentService.get_agent(db, publication.agent_id)
    if agent is None or not agent.is_available:
        raise NotFoundException(f"Published agent with slug {slug} not found")

    if request.attachment_ids and request.conversation_id is None:
        raise ValidationException("附件需要有效的公开会话")
    attachment_context = ""
    if request.conversation_id is not None:
        attachment_context = public_conversation_attachment_service.context_for_message(
            conversation_id=request.conversation_id,
            token=x_public_conversation_token,
            agent_id=str(publication.agent_id),
            slug=slug,
            file_ids=request.attachment_ids,
        )

    team_id = str(publication.team_id)
    rate_status = await competition_manager_service.check_team_rate_limit(team_id)
    if rate_status == LimitStatus.EXCEEDED:
        raise QuotaException("Rate limit exceeded. Please wait and try again.", code=ResponseCode.RATE_LIMIT_EXCEEDED)
    if rate_status == LimitStatus.INFRA_ERROR:
        raise Exception("Internal service error during rate limit validation.")

    token_status = await competition_manager_service.check_team_token_limit(team_id)
    if token_status == LimitStatus.EXCEEDED:
        raise QuotaException("Token quota exhausted for this team.", code=ResponseCode.QUOTA_EXCEEDED)
    if token_status == LimitStatus.INFRA_ERROR:
        raise Exception("Internal service error during quota validation.")

    request_id = get_request_id()
    execution_id = uuid.uuid4()
    auth = AuthContext(
        user_id=f"public:{request.conversation_id or publication.slug}",
        team_id=team_id,
        auth_mode="public_link",
        request_id=request_id,
        role="public",
        is_dev=False,
    )
    await execution_log_service.start_execution(
        execution_id=execution_id,
        agent_id=publication.agent_id,
        team_id=publication.team_id,
        request_id=request_id,
        initial_state=ExecutionState.INIT.value,
        input_data=request.input,
    )

    async def run_execution_in_background() -> None:
        task = asyncio.current_task()
        if task is not None:
            execution_cancellation_service.register(execution_id, task)
        try:
            await execution_engine.run(
                agent_id=str(publication.agent_id),
                user_input=request.input,
                auth_context=auth,
                request_id=request_id,
                conversation_history=request.conversation_history,
                confirmed_tool_actions=[],
                policy_overrides=None,
                execution_id=execution_id,
                start_log=False,
                attachment_context=attachment_context,
            )
        except asyncio.CancelledError:
            await execution_log_service.terminate_if_active(
                execution_id=execution_id,
                final_answer="已停止：公开链接执行已取消。",
                termination_reason=TerminationReason.USER_STOPPED.value,
                team_id=publication.team_id,
            )
            raise
        except Exception as exc:
            logger.exception(f"Public link execution failed before completion: {exc}")
            error = ExecutionErrorModel(
                error_code=ResponseCode.ENGINE_ERROR.name,
                error_source="execution_engine",
                error_message=str(exc),
            )
            await execution_log_service.complete_execution(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED.value,
                final_state=ExecutionState.TERMINATED.value,
                termination_reason=TerminationReason.FAILED.value,
                steps_used=0,
                final_answer=f"执行失败：{exc}",
                total_token_usage=TokenUsage(),
                error=error,
            )
        finally:
            execution_cancellation_service.unregister(execution_id)

    background_tasks.add_task(run_execution_in_background)
    return BaseResponse.success(
        data=ExecuteAgentResponse(
            execution_id=execution_id,
            final_state=ExecutionState.INIT,
            termination_reason=None,
            steps_used=0,
            request_id=request_id,
        ),
        message="OK",
    )
