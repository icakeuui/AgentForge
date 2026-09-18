import pytest
from fastapi.testclient import TestClient
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from backend.core.config import settings
from backend.models.constants import ResponseCode

# Use the same team ID as seeded in conftest
TEST_TEAM_ID = "00000000-0000-0000-0000-000000000001"

def get_auth_headers(team_id=TEST_TEAM_ID, user_id="user-integration"):
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

def test_create_and_get_agent(client: TestClient, auth_headers):
    # 1. Create Agent
    payload = {
        "system_prompt": "You are a test agent.",
        "model_config": {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7
        },
        "tools": ["calculator"]
    }
    response = client.post("/agents", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    agent_id = data["data"]["id"]
    assert agent_id is not None

    # 2. Get Agent
    response = client.get(f"/agents/{agent_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["system_prompt"] == "You are a test agent."
    assert data["data"]["model_config"]["model"] == "gpt-3.5-turbo"
    
    # 3. Get Non-existent Agent
    fake_id = str(uuid.uuid4())
    response = client.get(f"/agents/{fake_id}", headers=auth_headers)
    assert response.status_code == 404
    # ResponseCode.NOT_FOUND is 1002
    expected_code = ResponseCode.NOT_FOUND.value if hasattr(ResponseCode.NOT_FOUND, "value") else ResponseCode.NOT_FOUND
    assert response.json()["code"] == expected_code

    # 4. Invalid UUID
    response = client.get("/agents/not-a-uuid", headers=auth_headers)
    assert response.status_code == 422
    # VALIDATION_ERROR is 1001
    expected_code = ResponseCode.VALIDATION_ERROR.value if hasattr(ResponseCode.VALIDATION_ERROR, "value") else ResponseCode.VALIDATION_ERROR
    assert response.json()["code"] == expected_code
