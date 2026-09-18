import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from backend.core.config import settings
from backend.main import app
from backend.models.constants import ResponseCode
from backend.models.orm import AgentOwnership
from tests.conftest import TEST_TEAM_B_ID, TEST_TEAM_ID, TestingSessionLocal


class _FakeMarketplaceAPI:
    async def list_extensions(self):
        return []

    async def get_extension(self, extension_id: str):
        return {"id": extension_id, "name": "fake", "version": "1.0.0"}

    async def list_extension_tools(self, extension_id: str):
        return []

    async def test_extension_connection(self, extension_id: str, config: dict):
        return True, "ok"

    async def get_tool_schemas(self):
        return {}

    async def install_extension(self, extension_id: str, user_id: str, config: dict):
        return None

    async def uninstall_extension(self, extension_id: str, user_id: str):
        return None

    async def list_user_extensions(self, user_id: str):
        return []

    async def execute_tool(self, tool_id: str, arguments: dict, context: dict | None = None):
        return {"ok": True, "tool_id": tool_id, "context": context or {}}

    async def get_tools_for_agent(self, agent_id: str):
        return [{"id": "calculator/add"}]

    async def bind_tools_to_agent(self, agent_id: str, tool_ids: list[str]):
        return None

    async def unbind_tools_from_agent(self, agent_id: str, tool_ids: list[str]):
        return None


def _auth_headers(team_id: str, user_id: str) -> dict[str, str]:
    payload = {
        "user_id": user_id,
        "team_id": team_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _inject_fake_marketplace_api():
    app.state.pm_api = _FakeMarketplaceAPI()
    yield
    if hasattr(app.state, "pm_api"):
        delattr(app.state, "pm_api")


@pytest.mark.asyncio
async def test_marketplace_same_team_user_access_success():
    headers = _auth_headers(str(TEST_TEAM_ID), "user-integration")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/marketplace/users/user-team-a-2/extensions",
            headers=headers,
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_marketplace_cross_team_user_access_denied():
    headers = _auth_headers(str(TEST_TEAM_ID), "user-integration")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/marketplace/users/user-team-b-1/extensions",
            headers=headers,
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == ResponseCode.TEAM_FORBIDDEN.value


@pytest.mark.asyncio
async def test_marketplace_execute_cannot_bypass_team_by_context_user():
    headers = _auth_headers(str(TEST_TEAM_ID), "user-integration")
    payload = {
        "tool_id": "demo/tool",
        "arguments": {"x": 1},
        "context": {"user_id": "user-team-b-1"},
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/marketplace/tools/execute",
            json=payload,
            headers=headers,
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == ResponseCode.TEAM_FORBIDDEN.value


@pytest.mark.asyncio
async def test_marketplace_query_tools_cross_team_agent_denied():
    cross_team_agent_id = uuid.uuid4()
    async with TestingSessionLocal() as session:
        session.add(AgentOwnership(agent_id=cross_team_agent_id, team_id=TEST_TEAM_B_ID))
        await session.commit()

    headers = _auth_headers(str(TEST_TEAM_ID), "user-integration")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/marketplace/agents/{cross_team_agent_id}/tools",
            headers=headers,
        )
    assert resp.status_code == 403
    assert resp.json()["code"] == ResponseCode.TEAM_FORBIDDEN.value
