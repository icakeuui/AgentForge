from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.rate_limiter import LimitStatus
from backend.services.competition_manager_service import competition_manager_service
from backend.services.execution_engine import execution_engine


TEST_TEAM_ID = "00000000-0000-0000-0000-000000000001"


def _auth_headers(user_id: str = "user-integration") -> dict[str, str]:
    payload = {
        "user_id": user_id,
        "team_id": TEST_TEAM_ID,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def _create_agent(client: TestClient, name: str = "Public Link Agent") -> str:
    response = client.post(
        "/agents",
        json={
            "name": name,
            "description": "Answers public visitors with a concise product voice.",
            "opening_statement": "你好，我可以公开接待访客。",
            "avatar_url": "https://example.com/avatar.png",
            "llm_provider_url": "https://example.com/v1",
            "llm_api_key": "test-key",
            "llm_model_name": "gpt-4o-mini",
            "runtime_config": {"temperature": 0.2},
            "capability_flags": {"supports_tools": False},
            "tools": [],
            "constraints": {"max_steps": 4},
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 200
    return response.json()["data"]["id"]


def test_public_agent_square_lists_only_active_publications(client: TestClient):
    active_agent_id = _create_agent(client, name="Active Square Agent")
    disabled_agent_id = _create_agent(client, name="Disabled Square Agent")

    client.post(
        f"/agents/{active_agent_id}/publish",
        json={"slug": "active-square-agent", "title": "Active Square Agent"},
        headers=_auth_headers(),
    )
    client.post(
        f"/agents/{disabled_agent_id}/publish",
        json={"slug": "disabled-square-agent", "title": "Disabled Square Agent"},
        headers=_auth_headers(),
    )
    client.delete(f"/agents/{disabled_agent_id}/publish", headers=_auth_headers())

    response = client.get("/public/agents")

    assert response.status_code == 200
    records = response.json()["data"]
    assert [record["slug"] for record in records] == ["active-square-agent"]
    assert records[0]["title"] == "Active Square Agent"
    assert records[0]["opening_statement"] == "你好，我可以公开接待访客。"
    assert "agent_id" not in records[0]
    assert "team_id" not in records[0]


def test_publish_agent_creates_public_profile_and_can_be_disabled(client: TestClient):
    agent_id = _create_agent(client)

    publish_response = client.post(
        f"/agents/{agent_id}/publish",
        json={
            "title": "Public Support Agent",
            "description": "Use this assistant from a public link.",
            "slug": "public-support-agent",
        },
        headers=_auth_headers(),
    )

    assert publish_response.status_code == 200
    published = publish_response.json()["data"]
    assert published["agent_id"] == agent_id
    assert published["slug"] == "public-support-agent"
    assert published["status"] == "ACTIVE"
    assert published["public_url"] == "/p/public-support-agent"

    public_response = client.get("/public/agents/public-support-agent")
    assert public_response.status_code == 200
    public_profile = public_response.json()["data"]
    assert public_profile == {
        "slug": "public-support-agent",
        "title": "Public Support Agent",
        "description": "Use this assistant from a public link.",
        "opening_statement": "你好，我可以公开接待访客。",
        "avatar_url": "https://example.com/avatar.png",
    }

    disable_response = client.delete(f"/agents/{agent_id}/publish", headers=_auth_headers())
    assert disable_response.status_code == 200
    assert disable_response.json()["data"]["status"] == "DISABLED"

    disabled_public_response = client.get("/public/agents/public-support-agent")
    assert disabled_public_response.status_code == 404


def test_public_execute_starts_agent_execution_for_active_publication(monkeypatch, client: TestClient):
    monkeypatch.setattr(competition_manager_service, "check_team_rate_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    monkeypatch.setattr(competition_manager_service, "check_team_token_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    run_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(execution_engine, "run", run_mock)

    agent_id = _create_agent(client)
    client.post(
        f"/agents/{agent_id}/publish",
        json={"slug": "public-execute-agent"},
        headers=_auth_headers(),
    )

    response = client.post(
        "/public/agents/public-execute-agent/execute",
        json={
            "input": "请介绍你自己",
            "conversation_history": [{"role": "user", "content": "你好"}],
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_id"]
    assert data["request_id"]
    run_mock.assert_awaited_once()
    call_kwargs = run_mock.await_args.kwargs
    assert call_kwargs["agent_id"] == agent_id
    assert call_kwargs["user_input"] == "请介绍你自己"
    assert call_kwargs["auth_context"].team_id == TEST_TEAM_ID
    assert call_kwargs["auth_context"].auth_mode == "public_link"

    replay_response = client.get(f"/public/agents/public-execute-agent/executions/{data['execution_id']}")
    assert replay_response.status_code == 200
    replay = replay_response.json()["data"]
    assert replay["execution_id"] == data["execution_id"]
    assert replay["agent_id"] == agent_id
