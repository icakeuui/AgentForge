import asyncio
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_db
from backend.core.logging import get_request_id, logger
from backend.services.agent_service import AgentService
from backend.services.agent_runtime_defaults import default_agent_tool_ids
from backend.services.execution_engine import execution_engine
from backend.services.execution_log_service import execution_log_service
from backend.services.execution_cancellation_service import execution_cancellation_service
from backend.services.competition_manager_service import competition_manager_service
from backend.services.marketplace_tool_adapter import marketplace_tool_adapter
from backend.services.policy_gate import policy_gate
from backend.services.retrieval_policy_service import retrieval_policy_service
from backend.services.tool_need_classifier import tool_need_classifier
from backend.services.authorization_service import authorization_service
from backend.core.rate_limiter import LimitStatus
from backend.models.schemas import (
    AgentCreateRequest,
    AgentRead,
    AgentUpdateRequest,
    AuthContext,
    BaseResponse,
    AgentCreateResponse,
    ExecuteAgentRequest,
    ExecuteAgentResponse,
    ExecutionErrorModel,
    PublishedAgentRead,
    PublishedAgentUpsertRequest,
    TokenUsage,
)
from backend.models.constants import ExecutionState, ExecutionStatus, ResponseCode, TerminationReason

from backend.api.dependencies import get_current_user
from backend.core.exceptions import NotFoundException, QuotaException
from backend.core.exceptions import ValidationException
from backend.services.published_agent_service import published_agent_service

router = APIRouter(prefix="/agents", tags=["Agents"])


async def _validate_requested_tools(tool_ids: list[str]) -> None:
    resolution = await marketplace_tool_adapter.validate_tool_ids(tool_ids)
    if resolution.missing_tool_ids:
        raise ValidationException(f"Invalid tool ids: {', '.join(resolution.missing_tool_ids)}")


def _effective_tool_ids(*, supports_tools: bool, tool_ids: list[str]) -> list[str]:
    if supports_tools and not tool_ids:
        return default_agent_tool_ids()
    return tool_ids

@router.post("", response_model=BaseResponse[AgentCreateResponse])
async def create_agent(
    config: AgentCreateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    Create a new agent with strict contract validation.
    """
    await authorization_service.validate_membership(auth)
    effective_tool_ids = _effective_tool_ids(
        supports_tools=config.capability_flags.supports_tools,
        tool_ids=list(config.tools),
    )
    if effective_tool_ids:
        await _validate_requested_tools(effective_tool_ids)
    config = config.model_copy(update={"tools": effective_tool_ids})
    agent = await AgentService.create_agent(db, config, team_id=auth.team_id)
    await marketplace_tool_adapter.sync_agent_tools(str(agent.id), effective_tool_ids)
    logger.bind(resource_type="agent", resource_id=str(agent.id)).info(
        f"resource access log: create agent {agent.id}"
    )
    return BaseResponse.success(
        data=AgentCreateResponse(id=agent.id),
        message="Created successfully"
    )

@router.get("", response_model=BaseResponse[list[AgentRead]])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await authorization_service.validate_membership(auth)
    agents = await AgentService.list_agents(db, team_id=auth.team_id)
    return BaseResponse.success(data=agents, message="OK")

@router.get("/{id}", response_model=BaseResponse[AgentRead])
async def get_agent(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    """
    Get agent details.
    """
    agent = await AgentService.get_agent(db, id)
    if not agent:
        raise NotFoundException(f"Agent with ID {id} not found")
    await authorization_service.ensure_agent_ownership(auth, id, operation="read")
    logger.bind(resource_type="agent", resource_id=str(id)).info(
        f"resource access log: read agent {id}"
    )
    return BaseResponse.success(data=agent, message="OK")


@router.patch("/{id}", response_model=BaseResponse[AgentRead])
async def patch_agent(
    id: uuid.UUID,
    payload: AgentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await authorization_service.ensure_agent_ownership(auth, id, operation="update")
    if payload.tools is not None:
        await _validate_requested_tools(payload.tools)
    agent = await AgentService.update_agent(db, id, payload)
    if not agent:
        raise NotFoundException(f"Agent with ID {id} not found")
    if payload.tools is not None:
        await marketplace_tool_adapter.sync_agent_tools(str(id), payload.tools)
    return BaseResponse.success(data=agent, message="Updated successfully")


@router.put("/{id}", response_model=BaseResponse[AgentRead])
async def put_agent(
    id: uuid.UUID,
    payload: AgentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await authorization_service.ensure_agent_ownership(auth, id, operation="update")
    if payload.tools is not None:
        await _validate_requested_tools(payload.tools)
    agent = await AgentService.update_agent(db, id, payload)
    if not agent:
        raise NotFoundException(f"Agent with ID {id} not found")
    if payload.tools is not None:
        await marketplace_tool_adapter.sync_agent_tools(str(id), payload.tools)
    return BaseResponse.success(data=agent, message="Updated successfully")


@router.delete("/{id}", response_model=BaseResponse[AgentRead])
async def delete_agent(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await authorization_service.ensure_agent_ownership(auth, id, operation="update")
    agent = await AgentService.delete_agent(db, id)
    if not agent:
        raise NotFoundException(f"Agent with ID {id} not found")
    return BaseResponse.success(data=agent, message="Deleted successfully")


@router.get("/{id}/publish", response_model=BaseResponse[PublishedAgentRead])
async def get_agent_publication(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await authorization_service.ensure_agent_ownership(auth, id, operation="read_publication")
    publication = await published_agent_service.get_by_agent(db, id, uuid.UUID(auth.team_id))
    if publication is None:
        raise NotFoundException(f"Publication for agent {id} not found")
    return BaseResponse.success(data=publication, message="OK")


@router.post("/{id}/publish", response_model=BaseResponse[PublishedAgentRead])
async def publish_agent(
    id: uuid.UUID,
    payload: PublishedAgentUpsertRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    agent = await AgentService.get_agent(db, id)
    if not agent:
        raise NotFoundException(f"Agent with ID {id} not found")
    await authorization_service.ensure_agent_ownership(auth, id, operation="publish")
    publication = await published_agent_service.upsert(
        db,
        agent=agent,
        team_id=uuid.UUID(auth.team_id),
        payload=payload,
    )
    return BaseResponse.success(data=publication, message="Published successfully")


@router.patch("/{id}/publish", response_model=BaseResponse[PublishedAgentRead])
async def update_agent_publication(
    id: uuid.UUID,
    payload: PublishedAgentUpsertRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    agent = await AgentService.get_agent(db, id)
    if not agent:
        raise NotFoundException(f"Agent with ID {id} not found")
    await authorization_service.ensure_agent_ownership(auth, id, operation="update_publication")
    publication = await published_agent_service.upsert(
        db,
        agent=agent,
        team_id=uuid.UUID(auth.team_id),
        payload=payload,
    )
    return BaseResponse.success(data=publication, message="Updated successfully")


@router.delete("/{id}/publish", response_model=BaseResponse[PublishedAgentRead])
async def disable_agent_publication(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await authorization_service.ensure_agent_ownership(auth, id, operation="disable_publication")
    publication = await published_agent_service.disable(db, agent_id=id, team_id=uuid.UUID(auth.team_id))
    return BaseResponse.success(data=publication, message="Disabled successfully")

@router.post("/{id}/execute", response_model=BaseResponse[ExecuteAgentResponse])
async def execute_agent(
    id: uuid.UUID,
    request: ExecuteAgentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user)
):
    agent = await AgentService.get_agent(db, id)
    if not agent:
        raise NotFoundException(f"Agent with ID {id} not found")
    await authorization_service.ensure_agent_ownership(auth, id, operation="execute")
    if request.policy_overrides and not auth.is_dev:
        raise ValidationException("policy_overrides is only available in dev mode")
    team_id = auth.team_id
    
    # Check rate limit
    rate_status = await competition_manager_service.check_team_rate_limit(team_id)
    if rate_status == LimitStatus.EXCEEDED:
        raise QuotaException("Rate limit exceeded. Please wait and try again.", code=ResponseCode.RATE_LIMIT_EXCEEDED)
    if rate_status == LimitStatus.INFRA_ERROR:
        # Will be caught by global handler
        raise Exception("Internal service error during rate limit validation.")
        
    # Check token limit
    token_status = await competition_manager_service.check_team_token_limit(team_id)
    if token_status == LimitStatus.EXCEEDED:
        raise QuotaException("Token quota exhausted for this team.", code=ResponseCode.QUOTA_EXCEEDED)
    if token_status == LimitStatus.INFRA_ERROR:
        raise Exception("Internal service error during quota validation.")
        
    request_id = get_request_id()
    execution_id = uuid.uuid4()
    logger.bind(resource_type="execution_record", resource_id=str(id)).info(
        f"execution trace log: start execute agent={id}"
    )
    await execution_log_service.start_execution(
        execution_id=execution_id,
        agent_id=agent.id,
        team_id=uuid.UUID(auth.team_id),
        request_id=request_id,
        initial_state=ExecutionState.INIT.value,
        input_data=request.input,
    )

    async def run_execution_in_background() -> None:
        task = asyncio.current_task()
        if task is not None:
            execution_cancellation_service.register(execution_id, task)
        if execution_cancellation_service.is_cancelled(execution_id):
            await execution_log_service.terminate_if_active(
                execution_id=execution_id,
                final_answer="已停止：用户主动停止了当前模型行为。",
                termination_reason=TerminationReason.USER_STOPPED.value,
                team_id=uuid.UUID(auth.team_id),
            )
            return
        try:
            await execution_engine.run(
                agent_id=str(agent.id),
                user_input=request.input,
                auth_context=auth,
                request_id=request_id,
                conversation_history=request.conversation_history,
                confirmed_tool_actions=request.confirmed_tool_actions,
                policy_overrides=request.policy_overrides,
                execution_id=execution_id,
                start_log=False,
            )
        except asyncio.CancelledError:
            await execution_log_service.terminate_if_active(
                execution_id=execution_id,
                final_answer="已停止：用户主动停止了当前模型行为。",
                termination_reason=TerminationReason.USER_STOPPED.value,
                team_id=uuid.UUID(auth.team_id),
            )
            raise
        except Exception as exc:
            logger.exception(f"Background execution failed before completion: {exc}")
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
            final_state="INIT",
            termination_reason=None,
            steps_used=0,
            request_id=request_id
        ),
        message="OK"
    )


@router.post("/{id}/policy/inspect", response_model=BaseResponse[dict])
async def inspect_agent_policy(
    id: uuid.UUID,
    request: ExecuteAgentRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    if not auth.is_dev:
        raise ValidationException("policy inspect is only available in dev mode")
    raw_agent = await AgentService.get_agent_raw(db, id)
    if raw_agent is None:
        raise NotFoundException(f"Agent with ID {id} not found")
    await authorization_service.ensure_agent_ownership(auth, id, operation="execute")
    agent_config = raw_agent.config or {}
    runtime = await marketplace_tool_adapter.resolve_agent_runtime(
        agent_id=str(id),
        agent_config=agent_config,
        user_input=request.input,
    )
    tool_names = [
        str(((tool.get("function") or {}).get("name", ""))).strip()
        for tool in runtime.tool_schemas
        if isinstance(tool, dict)
    ]
    classification = tool_need_classifier.classify(
        request.input,
        agent_config=agent_config,
        tool_catalog_summary=tool_names,
    )
    retrieval_policy = retrieval_policy_service.resolve(classification)
    pre_policy = policy_gate.evaluate_pre_policy(
        classification=classification,
        retrieval_policy=retrieval_policy,
        bound_tool_ids=runtime.bound_tool_ids or runtime.resolved_tool_names,
        tool_catalog_entries=runtime.tool_catalog_entries,
        confirmed_tool_actions=request.confirmed_tool_actions,
    )
    return BaseResponse.success(
        data={
            "classification": classification.model_dump(),
            "retrieval_policy": retrieval_policy.model_dump(),
            "pre_policy": pre_policy.model_dump(),
            "allowed_tool_ids_for_turn": pre_policy.allowed_tool_ids_for_turn,
        },
        message="OK",
    )
