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
        user_id="user-tool-policy",
        team_id=TEST_TEAM_ID,
        auth_mode="jwt",
        request_id="req-tool-policy",
    )


def _schema(tool_id: str) -> dict:
    if tool_id == "builtin/websearch":
        parameters = {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 5}},
            "required": ["query"],
            "additionalProperties": False,
        }
    elif tool_id == "builtin/python_exec":
        parameters = {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
            "additionalProperties": False,
        }
    else:
        parameters = {"type": "object"}
    return {"type": "function", "function": {"name": tool_id, "description": tool_id, "parameters": parameters}}


def _catalog_entry(tool_id: str, *, domains: list[str], side_effect: str, requires_confirmation: bool) -> dict:
    return {
        "id": tool_id,
        "openai_schema": _schema(tool_id),
        "input_schema": _schema(tool_id)["function"]["parameters"],
        "risk_level": "high" if requires_confirmation else "medium",
        "side_effect": side_effect,
        "requires_confirmation": requires_confirmation,
        "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
        "domains": domains,
        "max_calls_per_run": 2,
    }


async def _create_agent(db_session) -> uuid.UUID:
    agent_id = uuid.uuid4()
    db_session.add(
        Agent(
            id=agent_id,
            config={
                "name": "Tool Policy Agent",
                "description": "Tool policy integration test agent",
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
    catalog = [
        _catalog_entry("builtin/websearch", domains=["web_search"], side_effect="external_read", requires_confirmation=False),
        _catalog_entry("builtin/python_exec", domains=["python"], side_effect="write", requires_confirmation=True),
    ]
    return ResolvedAgentRuntime(
        agent_id=str(agent_id),
        agent_config={"capability_flags": {"supports_tools": True}, "constraints": {"max_steps": 4}},
        supports_tools=True,
        tool_schemas=[entry["openai_schema"] for entry in catalog],
        resolved_tool_names=[entry["id"] for entry in catalog],
        max_steps=4,
        tool_catalog_entries=catalog,
        bound_tool_ids=[entry["id"] for entry in catalog],
    )


@pytest.mark.asyncio
async def test_tool_scope_exposes_policy_authorized_candidates_for_model_selection(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    model_gateway.call.return_value = GatewayResponse(
        content="已准备使用网页搜索。",
        token_usage=TokenUsage(total_tokens=5),
        finish_reason="stop",
    )
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _runtime(agent_id)
    strategy = LangGraphExecutionStrategy(model_gateway=model_gateway, tool_runtime=tool_runtime, execution_log_service=execution_log_service)

    await strategy.run(
        agent_id=str(agent_id),
        user_input="用 websearch 查 Cursor 最新文档",
        auth_context=_auth_context(),
        request_id="req-tool-scope-websearch",
    )

    tools = model_gateway.call.await_args.kwargs["tools"]
    assert [tool["function"]["name"] for tool in tools] == ["builtin/websearch", "builtin/python_exec"]


@pytest.mark.asyncio
async def test_unconfirmed_high_risk_tool_is_exposed_but_blocked_before_runtime(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    model_gateway.call.side_effect = [
        GatewayResponse(
            content="准备执行。",
            token_usage=TokenUsage(total_tokens=5),
            finish_reason="tool_calls",
            tool_calls=[
                {
                    "id": "call-python",
                    "function_name": "builtin/python_exec",
                    "function_arguments": '{"code": "print(1)"}',
                }
            ],
        ),
        GatewayResponse(
            content="该工具需要确认后才能执行。",
            token_usage=TokenUsage(total_tokens=5),
            finish_reason="stop",
        ),
    ]
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _runtime(agent_id)
    strategy = LangGraphExecutionStrategy(model_gateway=model_gateway, tool_runtime=tool_runtime, execution_log_service=execution_log_service)

    await strategy.run(
        agent_id=str(agent_id),
        user_input="请调用 builtin/python_exec 执行代码",
        auth_context=_auth_context(),
        request_id="req-tool-scope-python",
    )

    first_call_tools = model_gateway.call.await_args_list[0].kwargs["tools"]
    assert [tool["function"]["name"] for tool in first_call_tools] == ["builtin/websearch", "builtin/python_exec"]
    tool_runtime.execute_tool.assert_not_called()


@pytest.mark.asyncio
async def test_tool_policy_gate_blocks_invalid_arguments_before_runtime(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    model_gateway.call.side_effect = [
        GatewayResponse(
            content="需要搜索。",
            token_usage=TokenUsage(total_tokens=5),
            finish_reason="tool_calls",
            tool_calls=[
                {
                    "id": "call-invalid-websearch",
                    "function_name": "builtin/websearch",
                    "function_arguments": '{"limit": 3}',
                }
            ],
        ),
        GatewayResponse(
            content="工具参数不完整，无法搜索。",
            token_usage=TokenUsage(total_tokens=5),
            finish_reason="stop",
        ),
    ]
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _runtime(agent_id)
    strategy = LangGraphExecutionStrategy(model_gateway=model_gateway, tool_runtime=tool_runtime, execution_log_service=execution_log_service)

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="用 websearch 查 Cursor 最新文档",
        auth_context=_auth_context(),
        request_id="req-tool-invalid-args",
    )

    tool_runtime.execute_tool.assert_not_called()
    gate_logs = [log for log in result.step_logs if log.phase == "tool_policy_gate" and log.status == "error"]
    assert gate_logs
    assert gate_logs[0].payload["reason_code"] == "TOOL_ARGUMENT_SCHEMA_INVALID"
    assert gate_logs[0].payload["arguments_hash"]
    assert gate_logs[0].payload["arguments_summary"] == '{"limit": 3}'
