import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from backend.core.security import encrypt_api_key
from backend.core.tool_runtime import ToolExecutor
from backend.core.tools import EchoTool, PythonAddTool
from backend.models.constants import ExecutionStatus
from backend.models.orm import Agent, AgentOwnership
from backend.models.schemas import AuthContext, GatewayResponse, GatewayToolCall, TokenUsage
from backend.models.tool import ToolFailureResponse, ToolSuccessResponse
from backend.models.tool_runtime_errors import ToolRuntimeErrorCode
from backend.services.execution_log_service import execution_log_service
from backend.services.langgraph_execution_strategy import LangGraphExecutionStrategy

TEST_TEAM_ID = "00000000-0000-0000-0000-000000000001"


def _auth_context() -> AuthContext:
    return AuthContext(
        user_id="user-integration",
        team_id=TEST_TEAM_ID,
        auth_mode="jwt",
        request_id="req-test-tool-runtime",
    )


async def _create_agent(db_session) -> uuid.UUID:
    agent_id = uuid.uuid4()
    db_session.add(
        Agent(
            id=agent_id,
            config={
                "name": "Tool Runtime Agent",
                "description": "Tool runtime integration agent",
                "llm_provider_url": "https://example.com/v1",
                "llm_api_key_encrypted": encrypt_api_key("test-key"),
                "llm_model_name": "gpt-4o-mini",
                "runtime_config": {"temperature": 0.0},
                "capability_flags": {"supports_tools": True},
                "constraints": {"max_steps": 3},
            },
        )
    )
    db_session.add(AgentOwnership(agent_id=agent_id, team_id=uuid.UUID(TEST_TEAM_ID)))
    await db_session.commit()
    return agent_id


def test_tool_runtime_normal_tool_success():
    tool = EchoTool()
    with patch("backend.core.tool_runtime.ToolRegistry.get_tool", return_value=tool):
        resp = ToolExecutor.execute(name="echo_tool", input_data={"x": 1}, request_id="req-normal-tool")
    assert isinstance(resp, ToolSuccessResponse)
    assert resp.ok is True
    assert resp.data == {"y": 2}


def test_tool_runtime_python_tool_success():
    tool = PythonAddTool()
    with patch("backend.core.tool_runtime.ToolRegistry.get_tool", return_value=tool), patch(
        "backend.core.tools.sandbox_service.execute_python",
        return_value={"observation": {"value": 3}},
    ):
        resp = ToolExecutor.execute(name="python_add_tool", input_data={"x": 2}, request_id="req-python-tool-success")
    assert isinstance(resp, ToolSuccessResponse)
    assert resp.ok is True
    assert resp.data == {"observation": {"value": 3}}


def test_tool_runtime_sandbox_error_to_failure_response():
    tool = PythonAddTool()
    with patch("backend.core.tool_runtime.ToolRegistry.get_tool", return_value=tool), patch(
        "backend.core.tools.sandbox_service.execute_python",
        return_value={"observation": {"error": "division by zero"}},
    ):
        resp = ToolExecutor.execute(name="python_add_tool", input_data={"x": 2}, request_id="req-sandbox-error")
    assert isinstance(resp, ToolFailureResponse)
    assert resp.ok is False
    assert resp.error.code == ToolRuntimeErrorCode.SANDBOX_ERROR
    assert "division by zero" in resp.error.message


@pytest.mark.asyncio
async def test_strategy_preserves_tool_failure_as_observation(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.get_tools_schema.return_value = [
        {
            "type": "function",
            "function": {
                "name": "python_add_tool",
                "description": "Adds two integers",
                "parameters": {
                    "type": "object",
                    "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                    "required": ["a", "b"],
                    "additionalProperties": False,
                },
            },
        }
    ]
    tool_runtime.execute_tool.side_effect = RuntimeError("Sandbox execution failed: division by zero")
    model_gateway.call.side_effect = [
        GatewayResponse(
            content="必须先调用 python_add_tool。",
            token_usage=TokenUsage(total_tokens=10),
            finish_reason="tool_calls",
            tool_calls=[
                GatewayToolCall(
                    id="call-python-fail",
                    function_name="python_add_tool",
                    function_arguments='{"a":2,"b":0}',
                )
            ],
        ),
        GatewayResponse(content="工具失败了。", token_usage=TokenUsage(total_tokens=8), finish_reason="stop"),
    ]
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="trigger sandbox failure",
        auth_context=_auth_context(),
        request_id="req-tool-failure-compat",
    )

    replay = await execution_log_service.get_execution_replay(result.execution_id, team_id=uuid.UUID(TEST_TEAM_ID))
    assert result.status == ExecutionStatus.SUCCEEDED
    assert replay is not None
    assert replay["react_steps"][0]["observation"]["ok"] is False
    assert replay["react_steps"][0]["observation"]["error"]["message"] == "Sandbox execution failed: division by zero"
