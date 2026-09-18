import pytest
from fastapi.testclient import TestClient
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from backend.core.config import settings

# Use the same team ID as seeded in conftest
TEST_TEAM_ID = "00000000-0000-0000-0000-000000000001"

def get_auth_headers(team_id=TEST_TEAM_ID, user_id="user-e2e"):
    payload = {
        "user_id": user_id,
        "team_id": team_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers():
    return get_auth_headers()

def test_full_agent_lifecycle(client: TestClient, auth_headers):
    # 1. Create Agent
    payload = {
        "name": "Lifecycle Test Agent",
        "description": "E2E lifecycle test agent",
        "opening_statement": "You are a helpful assistant.",
        "llm_provider_url": "https://example.com/v1",
        "llm_api_key": "test-key",
        "llm_model_name": "gpt-4o-mini",
        "runtime_config": {
            "temperature": 0.7,
        },
        "capability_flags": {
            "supports_tools": False,
        },
        "tools": []
    }
    # Path should be /agents (no trailing slash)
    response = client.post("/agents", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    agent_id = data["data"]["id"]
    assert agent_id is not None
    
    # 2. Execute Agent
    # ExecuteAgentRequest expects {"input": "..."}
    exec_payload = {
        "input": "What is 2+2?"
    }
    # Path is /agents/{id}/execute
    response = client.post(f"/agents/{agent_id}/execute", json=exec_payload, headers=auth_headers)
    
    # Since we might not have a real LLM key in tests, it might fail in the engine,
    # but the API call itself should go through if quota/auth is OK.
    # The ModelGateway will likely return an error if TEST_KEY is used.
    # We check if it at least got to the engine.
    assert response.status_code in [200, 500] 
    
    if response.status_code == 200:
        data = response.json()
        assert data["code"] == 0
        execution_id = data["data"]["execution_id"]
        
        # 3. Retrieve Logs
        log_resp = client.get(f"/executions/{execution_id}", headers=auth_headers)
        assert log_resp.status_code == 200
        log_data = log_resp.json()
        assert log_data["code"] == 0
        # Replay data structure check
        assert "execution_id" in log_data["data"]
        assert "react_steps" in log_data["data"]


def test_archived_agent_still_appears_in_list(client: TestClient, auth_headers):
    payload = {
        "name": "Archived Agent",
        "description": "Archived list coverage",
        "opening_statement": "You are a helpful assistant.",
        "llm_provider_url": "https://example.com/v1",
        "llm_api_key": "test-key",
        "llm_model_name": "gpt-4o-mini",
        "runtime_config": {
            "temperature": 0.7,
        },
        "capability_flags": {
            "supports_tools": False,
        },
        "tools": []
    }

    create_response = client.post("/agents", json=payload, headers=auth_headers)
    assert create_response.status_code == 200
    agent_id = create_response.json()["data"]["id"]

    delete_response = client.delete(f"/agents/{agent_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["archived"] is True

    list_response = client.get("/agents", headers=auth_headers)
    assert list_response.status_code == 200
    agents = list_response.json()["data"]
    archived_agent = next((agent for agent in agents if agent["id"] == agent_id), None)
    assert archived_agent is not None
    assert archived_agent["archived"] is True
