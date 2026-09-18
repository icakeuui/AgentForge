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
        user_id="user-policy",
        team_id=TEST_TEAM_ID,
        auth_mode="jwt",
        request_id="req-policy",
    )


async def _create_agent(db_session) -> uuid.UUID:
    agent_id = uuid.uuid4()
    db_session.add(
        Agent(
            id=agent_id,
            config={
                "name": "Policy Agent",
                "description": "Policy integration test agent",
                "llm_provider_url": "https://example.com/v1",
                "llm_api_key_encrypted": encrypt_api_key("test-key"),
                "llm_model_name": "gpt-4o-mini",
                "runtime_config": {"temperature": 0.0},
                "capability_flags": {"supports_tools": True},
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
        agent_config={"capability_flags": {"supports_tools": True}, "constraints": {"max_steps": 4}},
        supports_tools=True,
        tool_schemas=[],
        resolved_tool_names=[],
        max_steps=4,
        bound_tool_ids=[],
    )


@pytest.mark.asyncio
async def test_required_kb_miss_returns_without_model_call(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
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
        request_id="req-kb-miss",
    )

    model_gateway.call.assert_not_called()
    assert "当前知识库未检索到" in (result.final_answer or "")
    assert any(log.phase == "intent_classification" for log in result.step_logs)
    assert any(log.phase == "retrieval_policy_gate" and log.status == "error" for log in result.step_logs)


@pytest.mark.asyncio
async def test_exact_clause_hit_injects_knowledge_context(db_session):
    agent_id = await _create_agent(db_session)
    await knowledge_service.create_document(
        db_session,
        agent_id=agent_id,
        team_id=uuid.UUID(TEST_TEAM_ID),
        title="学生管理规定",
        content="第一章 总则\n第十条 学生不得无故旷课，累计达到规定次数将按校规处理。\n第十一条 学生应按时参加考试。",
    )
    model_gateway = AsyncMock()
    model_gateway.call.return_value = GatewayResponse(
        content="第十条规定学生不得无故旷课。来源：学生管理规定 / 第十条",
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
        user_input="校规第10条是",
        auth_context=_auth_context(),
        request_id="req-kb-hit",
    )

    assert result.final_answer
    model_gateway.call.assert_called_once()
    retrieval_logs = [log for log in result.step_logs if log.phase == "knowledge_retrieval"]
    assert retrieval_logs
    assert retrieval_logs[0].payload["matched"] is True
    assert retrieval_logs[0].payload["knowledge_hits"][0]["match_type"] == "exact_clause"
