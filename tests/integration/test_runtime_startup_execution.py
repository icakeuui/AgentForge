from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.rate_limiter import LimitStatus
from backend.main import app
from backend.services.authorization_service import authorization_service
from backend.services.competition_manager_service import competition_manager_service
from backend.services.execution_engine import execution_engine
from backend.models.schemas import GatewayResponse, GatewayToolCall, TokenUsage

TEST_TEAM_ID = "00000000-0000-0000-0000-000000000001"


def _auth_headers(user_id: str = "user-integration") -> dict[str, str]:
    payload = {
        "user_id": user_id,
        "team_id": TEST_TEAM_ID,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_startup_materializes_builtin_tools_and_execution_uses_python_executor(monkeypatch):
    async def _allow(*args, **kwargs):
        return None

    monkeypatch.setattr(authorization_service, "validate_membership", _allow)
    monkeypatch.setattr(authorization_service, "ensure_agent_ownership", _allow)
    monkeypatch.setattr(authorization_service, "ensure_execution_record_ownership", _allow)
    monkeypatch.setattr(competition_manager_service, "check_team_rate_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    monkeypatch.setattr(competition_manager_service, "check_team_token_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    monkeypatch.setattr(
        execution_engine.strategy.model_gateway,
        "call",
        AsyncMock(
            side_effect=[
                GatewayResponse(
                    content="需要调用 python_executor。",
                    token_usage=TokenUsage(total_tokens=10),
                    finish_reason="tool_calls",
                    tool_calls=[
                        GatewayToolCall(
                            id="call-python-executor",
                            function_name="builtin/python_executor",
                            function_arguments='{"code":"result = {\\"sum\\": sum([1,2,3]), \\"max\\": max([1,2,3])}"}',
                        )
                    ],
                ),
                GatewayResponse(
                    content="结果为 sum=6, max=3。",
                    token_usage=TokenUsage(total_tokens=6),
                    finish_reason="stop",
                ),
            ]
        ),
    )

    agent_payload = {
        "name": "Runtime Startup Agent",
        "description": "Verifies startup-time builtin tool materialization",
        "llm_provider_url": "https://example.com/v1",
        "llm_api_key": "test-key",
        "llm_model_name": "gpt-4o-mini",
        "runtime_config": {"temperature": 0.0},
        "capability_flags": {"supports_tools": True},
        "tools": ["python_executor"],
        "constraints": {"max_steps": 4},
    }

    with TestClient(app) as client:
        schemas = client.get("/api/v1/marketplace/tools/schemas", headers=_auth_headers()).json()["tools"]
        assert any(tool["function"]["name"] == "builtin/python_executor" for tool in schemas)

        create_response = client.post("/agents", json=agent_payload, headers=_auth_headers())
        assert create_response.status_code == 200
        agent_id = create_response.json()["data"]["id"]

        execute_response = client.post(
            f"/agents/{agent_id}/execute",
            json={
                "input": '请调用 python_executor 执行以下代码并返回结果：result = {"sum": sum([1,2,3]), "max": max([1,2,3])}'
            },
            headers=_auth_headers(),
        )
        assert execute_response.status_code == 200
        execution_data = execute_response.json()["data"]

        replay_response = client.get(f"/executions/{execution_data['execution_id']}", headers=_auth_headers())
        assert replay_response.status_code == 200
        replay = replay_response.json()["data"]
        assert replay["steps_used"] > 0
        assert replay["react_steps"][0]["action"]["tool_id"] == "builtin/python_executor"


def test_startup_assigns_default_tools_to_tool_enabled_agents(monkeypatch):
    async def _allow(*args, **kwargs):
        return None

    monkeypatch.setattr(authorization_service, "validate_membership", _allow)

    with TestClient(app) as client:
        create_response = client.post(
            "/agents",
            json={
                "name": "Default Tool Agent",
                "description": "Should receive default builtin tools",
                "llm_provider_url": "https://example.com/v1",
                "llm_api_key": "test-key",
                "llm_model_name": "gpt-4o-mini",
                "runtime_config": {"temperature": 0.0},
                "capability_flags": {"supports_tools": True},
                "tools": [],
                "constraints": {"max_steps": 4},
            },
            headers=_auth_headers(),
        )
        assert create_response.status_code == 200
        agent_id = create_response.json()["data"]["id"]

        detail_response = client.get(f"/agents/{agent_id}", headers=_auth_headers())
        assert detail_response.status_code == 200
        detail = detail_response.json()["data"]
        assert detail["tools"] == ["websearch", "calculate"]


def test_agent_create_rejects_unknown_tool_ids_after_startup(monkeypatch):
    async def _allow(*args, **kwargs):
        return None

    monkeypatch.setattr(authorization_service, "validate_membership", _allow)

    with TestClient(app) as client:
        response = client.post(
            "/agents",
            json={
                "name": "Invalid Tool Agent",
                "description": "Should fail validation",
                "llm_provider_url": "https://example.com/v1",
                "llm_api_key": "test-key",
                "llm_model_name": "gpt-4o-mini",
                "runtime_config": {"temperature": 0.0},
                "capability_flags": {"supports_tools": True},
                "tools": ["builtin/not_real"],
                "constraints": {"max_steps": 4},
            },
            headers=_auth_headers(),
        )

        assert response.status_code == 422
        assert response.json()["message"] == "Invalid tool ids: builtin/not_real"
