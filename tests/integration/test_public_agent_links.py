from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.rate_limiter import LimitStatus
from backend.services.competition_manager_service import competition_manager_service
from backend.services.execution_engine import execution_engine
from backend.services.public_conversation_attachment_service import (
    LocalAttachmentStorage,
    public_conversation_attachment_service,
)


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


def test_new_agents_keep_existing_config_and_knowledge(client: TestClient):
    first_id = _create_agent(client, name="Knowledge Quiz Agent")
    first_document = client.post(
        f"/agents/{first_id}/knowledge",
        json={"title": "Quiz facts", "content": "The first agent's private facts."},
        headers=_auth_headers(),
    )
    assert first_document.status_code == 200

    second_id = _create_agent(client, name="Course Agent")
    third_id = _create_agent(client, name="Another Agent")
    assert len({first_id, second_id, third_id}) == 3

    second_update = client.patch(
        f"/agents/{second_id}",
        json={"description": "Only the second agent changed."},
        headers=_auth_headers(),
    )
    assert second_update.status_code == 200
    agents = client.get("/agents", headers=_auth_headers()).json()["data"]
    assert {first_id, second_id, third_id}.issubset({agent["id"] for agent in agents})
    first = client.get(f"/agents/{first_id}", headers=_auth_headers()).json()["data"]
    second = client.get(f"/agents/{second_id}", headers=_auth_headers()).json()["data"]
    assert first["name"] == "Knowledge Quiz Agent"
    assert first["description"] != second["description"]
    assert len(client.get(f"/agents/{first_id}/knowledge", headers=_auth_headers()).json()["data"]) == 1
    assert client.get(f"/agents/{second_id}/knowledge", headers=_auth_headers()).json()["data"] == []
    assert client.get(f"/agents/{third_id}/knowledge", headers=_auth_headers()).json()["data"] == []


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


def test_public_visitors_get_distinct_conversation_identity(monkeypatch, client: TestClient):
    monkeypatch.setattr(competition_manager_service, "check_team_rate_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    monkeypatch.setattr(competition_manager_service, "check_team_token_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    run_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(execution_engine, "run", run_mock)
    agent_id = _create_agent(client, name="Visitor Isolation Agent")
    client.post(f"/agents/{agent_id}/publish", json={"slug": "visitor-isolation-agent"}, headers=_auth_headers())

    visitors = [client.post("/public/agents/visitor-isolation-agent/conversations").json()["data"] for _ in range(2)]
    for visitor in visitors:
        response = client.post(
            "/public/agents/visitor-isolation-agent/execute",
            json={"input": "hello", "conversation_id": visitor["conversation_id"]},
            headers={"X-Public-Conversation-Token": visitor["conversation_token"]},
        )
        assert response.status_code == 200
    contexts = [call.kwargs["auth_context"] for call in run_mock.await_args_list]
    assert contexts[0].user_id != contexts[1].user_id
    assert all(context.auth_mode == "public_link" for context in contexts)


def test_public_attachment_reaches_execution_without_entering_agent_knowledge(monkeypatch, client: TestClient, tmp_path):
    monkeypatch.setattr(public_conversation_attachment_service, "storage", LocalAttachmentStorage(tmp_path))
    monkeypatch.setattr(competition_manager_service, "check_team_rate_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    monkeypatch.setattr(competition_manager_service, "check_team_token_limit", AsyncMock(return_value=LimitStatus.ALLOWED))
    run_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(execution_engine, "run", run_mock)

    agent_id = _create_agent(client, name="Attachment Public Agent")
    client.post(
        f"/agents/{agent_id}/publish",
        json={"slug": "attachment-public-agent"},
        headers=_auth_headers(),
    )
    first = client.post("/public/agents/attachment-public-agent/conversations").json()["data"]
    second = client.post("/public/agents/attachment-public-agent/conversations").json()["data"]
    upload_url = f"/public/agents/attachment-public-agent/conversations/{first['conversation_id']}/attachments"
    upload = client.post(
        upload_url,
        files={"file": ("private.txt", "只属于访客甲的内容".encode(), "text/plain")},
        headers={"X-Public-Conversation-Token": first["conversation_token"]},
    )
    assert upload.status_code == 200
    attachment_id = upload.json()["data"]["id"]

    denied = client.post(
        "/public/agents/attachment-public-agent/execute",
        json={"input": "总结附件", "conversation_id": first["conversation_id"], "attachment_ids": [attachment_id]},
        headers={"X-Public-Conversation-Token": second["conversation_token"]},
    )
    assert denied.status_code == 422
    run_mock.assert_not_awaited()

    response = client.post(
        "/public/agents/attachment-public-agent/execute",
        json={"input": "总结附件", "conversation_id": first["conversation_id"], "attachment_ids": [attachment_id]},
        headers={"X-Public-Conversation-Token": first["conversation_token"]},
    )
    assert response.status_code == 200
    assert "只属于访客甲的内容" in run_mock.await_args.kwargs["attachment_context"]
    assert run_mock.await_args.kwargs["user_input"] == "总结附件"
    knowledge = client.get(f"/agents/{agent_id}/knowledge", headers=_auth_headers()).json()["data"]
    assert knowledge == []
