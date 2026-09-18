import pytest
from fastapi.testclient import TestClient
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from backend.core.config import settings
from unittest.mock import AsyncMock, patch

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

def test_get_team_quota_success(client: TestClient, auth_headers):
    from backend.models.schemas import TeamQuotaStatusData
    from backend.models.constants import QuotaStatus
    
    mock_quota_data = TeamQuotaStatusData(
        team_id=TEST_TEAM_ID,
        token_limit=1000,
        token_used=100,
        rate_limit=5,
        current_usage_state="NORMAL",
        quota_status=QuotaStatus.ACTIVE
    )
    
    with patch("backend.api.routes.teams.competition_manager_service.get_team_quota_status", new_callable=AsyncMock) as mock_get_quota:
        mock_get_quota.return_value = mock_quota_data
        
        response = client.get(f"/teams/{TEST_TEAM_ID}/quota", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["team_id"] == TEST_TEAM_ID
        assert data["data"]["token_limit"] == 1000

def test_get_team_quota_forbidden(client: TestClient):
    other_team_id = str(uuid.uuid4())
    headers = get_auth_headers(team_id=other_team_id)
    
    # We need to mock the other team's existence for the auth check to pass
    class MockTeam:
        status = "ACTIVE"
        
    with patch("backend.api.dependencies.competition_manager_service.get_team", new_callable=AsyncMock) as mock_get_team:
        mock_get_team.return_value = MockTeam()
        
        # Accessing TEST_TEAM_ID while being in other_team_id should be forbidden
        response = client.get(f"/teams/{TEST_TEAM_ID}/quota", headers=headers)
        assert response.status_code == 403
        # ResponseCode.TEAM_FORBIDDEN is 5004
        assert response.json()["code"] == 5004
