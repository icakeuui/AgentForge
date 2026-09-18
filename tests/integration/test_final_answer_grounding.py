import uuid
from unittest.mock import AsyncMock

import pytest

from backend.core.security import encrypt_api_key
from backend.models.orm import Agent, AgentOwnership
from backend.models.schemas import AuthContext, GatewayResponse, TokenUsage
from backend.services.agent_runtime_assembler import ResolvedAgentRuntime
from backend.services.execution_log_service import execution_log_service
from backend.services.knowledge_service import knowledge_service
from backend.services.langgraph_execution_strategy import LangGraphExecutionStrategy


TEST_TEAM_ID = "00000000-0000-0000-0000-000000000001"


def _auth_context() -> AuthContext:
    return AuthContext(
        user_id="user-final-gate",
        team_id=TEST_TEAM_ID,
        auth_mode="jwt",
        request_id="req-final-gate",
    )


async def _create_agent(db_session) -> uuid.UUID:
    agent_id = uuid.uuid4()
    db_session.add(
        Agent(
            id=agent_id,
            config={
                "name": "Final Gate Agent",
                "description": "Policy integration test agent",
                "llm_provider_url": "https://example.com/v1",
                "llm_api_key_encrypted": encrypt_api_key("test-key"),
                "llm_model_name": "gpt-4o-mini",
                "runtime_config": {"temperature": 0.0},
                "capability_flags": {"supports_tools": False},
                "constraints": {"max_steps": 4},
            },
        )
    )
    db_session.add(AgentOwnership(agent_id=agent_id, team_id=uuid.UUID(TEST_TEAM_ID)))
    await db_session.commit()
    return agent_id


def _runtime(agent_id: uuid.UUID) -> ResolvedAgentRuntime:
    return ResolvedAgentRuntime(
        agent_id=str(agent_id),
        agent_config={"capability_flags": {"supports_tools": False}, "constraints": {"max_steps": 4}},
        supports_tools=False,
        tool_schemas=[],
        resolved_tool_names=[],
        max_steps=4,
        bound_tool_ids=[],
    )


@pytest.mark.asyncio
async def test_final_answer_gate_appends_missing_required_citation(db_session):
    agent_id = await _create_agent(db_session)
    await knowledge_service.create_document(
        db_session,
        agent_id=agent_id,
        team_id=uuid.UUID(TEST_TEAM_ID),
        title="学生管理规定",
        content="第一章 总则\n第十条 学生不得无故旷课，累计达到规定次数将按校规处理。",
    )
    model_gateway = AsyncMock()
    model_gateway.call.return_value = GatewayResponse(
        content="第十条规定学生不得无故旷课。",
        token_usage=TokenUsage(total_tokens=8),
        finish_reason="stop",
    )
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _runtime(agent_id)
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="校规第十条是",
        auth_context=_auth_context(),
        request_id="req-final-citation",
    )

    assert result.final_answer
    assert "学生管理规定 / 第十条" in result.final_answer
    assert any(
        log.phase == "final_answer_policy_gate"
        and log.payload.get("accepted") is False
        and log.payload.get("violation_code") == "MISSING_REQUIRED_CITATION"
        for log in result.step_logs
    )
