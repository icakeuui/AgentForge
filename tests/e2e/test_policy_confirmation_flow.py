import uuid
from unittest.mock import AsyncMock

import pytest

from backend.core.security import encrypt_api_key
from backend.models.orm import Agent, AgentOwnership
from backend.models.schemas import AuthContext, GatewayResponse, TokenUsage
from backend.services.agent_runtime_assembler import ResolvedAgentRuntime
from backend.services.execution_log_service import execution_log_service
from backend.services.langgraph_execution_strategy import LangGraphExecutionStrategy


TEST_TEAM_ID = "00000000-0000-0000-0000-000000000001"


def _auth_context() -> AuthContext:
    return AuthContext(
        user_id="user-e2e-policy",
        team_id=TEST_TEAM_ID,
        auth_mode="jwt",
        request_id="req-e2e-policy",
    )


async def _create_agent(db_session) -> uuid.UUID:
    agent_id = uuid.uuid4()
    db_session.add(
        Agent(
            id=agent_id,
            config={
                "name": "Policy Confirmation Agent",
                "description": "E2E policy confirmation test agent",
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
    schema = {
        "type": "function",
        "function": {
            "name": "builtin/python_exec",
            "description": "Execute Python code",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
                "additionalProperties": False,
            },
        },
    }
    return ResolvedAgentRuntime(
        agent_id=str(agent_id),
        agent_config={"capability_flags": {"supports_tools": True}, "constraints": {"max_steps": 4}},
        supports_tools=True,
        tool_schemas=[schema],
        resolved_tool_names=["builtin/python_exec"],
        max_steps=4,
        tool_catalog_entries=[
            {
                "id": "builtin/python_exec",
                "openai_schema": schema,
                "input_schema": schema["function"]["parameters"],
                "risk_level": "high",
                "side_effect": "write",
                "requires_confirmation": True,
                "allowed_intents": ["HIGH_RISK_TOOL", "TOOL_REQUIRED"],
                "domains": ["python"],
                "max_calls_per_run": 1,
            }
        ],
        bound_tool_ids=["builtin/python_exec"],
    )


@pytest.mark.asyncio
async def test_high_risk_tool_requires_intent_then_argument_confirmation(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    blocked_tool_call = GatewayResponse(
        content="准备执行清理。",
        token_usage=TokenUsage(total_tokens=5),
        finish_reason="tool_calls",
        tool_calls=[
            {
                "id": "call-python-delete",
                "function_name": "builtin/python_exec",
                "function_arguments": '{"code": "delete_all_temp_data()"}',
            }
        ],
    )
    model_gateway.call.side_effect = [
        blocked_tool_call,
        GatewayResponse(
            content="该工具动作需要用户确认后才能执行。",
            token_usage=TokenUsage(total_tokens=5),
            finish_reason="stop",
        ),
        blocked_tool_call,
        GatewayResponse(
            content="该工具动作需要参数级确认后才能执行。",
            token_usage=TokenUsage(total_tokens=5),
            finish_reason="stop",
        ),
    ]
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _runtime(agent_id)
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    first_result = await strategy.run(
        agent_id=str(agent_id),
        user_input="请用 python 删除全部临时数据",
        auth_context=_auth_context(),
        request_id="req-e2e-unconfirmed-intent",
    )

    model_gateway.call.assert_called()
    tool_runtime.execute_tool.assert_not_called()
    assert "确认" in (first_result.final_answer or "")
    assert any(
        log.phase == "tool_policy_gate" and log.payload.get("reason_code") == "TOOL_CONFIRMATION_REQUIRED"
        for log in first_result.step_logs
    )

    second_result = await strategy.run(
        agent_id=str(agent_id),
        user_input="请用 python 删除全部临时数据",
        auth_context=_auth_context(),
        request_id="req-e2e-confirmed-intent",
        confirmed_tool_actions=[
            {
                "tool_id": "builtin/python_exec",
                "arguments_hash": "intent-confirmed",
                "confirmed_at": "2026-04-28T00:00:00Z",
            }
        ],
    )

    model_gateway.call.assert_called()
    tool_runtime.execute_tool.assert_not_called()
    argument_gate_logs = [
        log
        for log in second_result.step_logs
        if log.phase == "tool_policy_gate" and log.payload.get("reason_code") == "TOOL_CONFIRMATION_REQUIRED"
    ]
    assert argument_gate_logs
    assert argument_gate_logs[0].payload["arguments_hash"]
    assert "delete_all_temp_data" in argument_gate_logs[0].payload["arguments_summary"]
