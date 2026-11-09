"""Exercise two accounts against the dedicated on-disk test database."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.core.config import settings
from backend.core import database as core_db
from backend.main import app
from backend.models.orm import Agent, AgentOwnership


@pytest.mark.asyncio
async def test_two_qq_accounts_login_isolation_and_password_reset(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    accounts = [
        ("agentforge-test-a@qq.com", "Account A", "A-password-123"),
        ("agentforge-test-b@qq.com", "Account B", "B-password-456"),
    ]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        registered = []
        for email, name, password in accounts:
            started = await client.post("/auth/register/start", json={"email": f" {email.upper()} ", "delivery_mode": "local"})
            assert started.status_code == 200, started.text
            code = started.json()["data"]["dev_code"]
            verified = await client.post("/auth/register/verify", json={"email": email, "code": code})
            assert verified.status_code == 200, verified.text
            completed = await client.post(
                "/auth/register/complete",
                json={
                    "email": email,
                    "registration_token": verified.json()["data"]["registration_token"],
                    "password": password,
                    "confirm_password": password,
                    "display_name": name,
                    "avatar_url": f"https://example.test/{name[-1].lower()}.png",
                },
            )
            assert completed.status_code == 200, completed.text
            registered.append(completed.json()["data"])

        assert registered[0]["user"]["user_id"] != registered[1]["user"]["user_id"]
        assert registered[0]["user"]["team_id"] != registered[1]["user"]["team_id"]
        agent_ids = []
        async with core_db.AsyncSessionLocal() as session:
            for index, pair in enumerate(registered):
                agent_id = uuid.uuid4()
                agent_ids.append(str(agent_id))
                session.add(Agent(id=agent_id, config={"name": f"Private agent {index}", "description": "test", "llm_model_name": "test-model"}))
                session.add(AgentOwnership(agent_id=agent_id, team_id=uuid.UUID(pair["user"]["team_id"])))
            await session.commit()
        for index in (0, 1, 0):
            email, name, password = accounts[index]
            logged_in = await client.post("/auth/login", json={"email": f" {email.upper()} ", "password": password})
            assert logged_in.status_code == 200, logged_in.text
            pair = logged_in.json()["data"]
            assert pair["user"]["user_id"] == registered[index]["user"]["user_id"]
            headers = {"Authorization": f"Bearer {pair['access_token']}"}
            profile = await client.get("/auth/session", headers=headers)
            assert profile.status_code == 200, profile.text
            assert profile.json()["data"]["display_name"] == name
            assert profile.json()["data"]["email"] == email
            assert profile.json()["data"]["avatar_url"] == f"https://example.test/{name[-1].lower()}.png"
            agents = await client.get("/agents", headers=headers)
            assert agents.status_code == 200, agents.text
            assert [agent["id"] for agent in agents.json()["data"]] == [agent_ids[index]]
            assert (await client.get(f"/agents/{agent_ids[1 - index]}", headers=headers)).status_code == 403
            assert (await client.post("/auth/logout", json={"refresh_token": pair["refresh_token"]})).status_code == 200

        a_headers = {"Authorization": f"Bearer {registered[0]['access_token']}"}
        b_headers = {"Authorization": f"Bearer {registered[1]['access_token']}"}
        changed = await client.patch("/auth/profile", json={"display_name": "Updated A", "avatar_url": "https://example.test/updated-a.png"}, headers=a_headers)
        assert changed.status_code == 200, changed.text
        b_profile = await client.get("/auth/session", headers=b_headers)
        assert b_profile.status_code == 200
        assert b_profile.json()["data"]["display_name"] == "Account B"
        assert b_profile.json()["data"]["avatar_url"] == "https://example.test/b.png"

        wrong = await client.post("/auth/login", json={"email": accounts[1][0], "password": accounts[0][2]})
        assert wrong.status_code == 401

        old_pair = registered[0]
        forgot = await client.post("/auth/password/forgot", json={"email": accounts[0][0]})
        assert forgot.status_code == 200, forgot.text
        reset_code = forgot.json()["data"]["dev_code"]
        reset = await client.post(
            "/auth/password/reset",
            json={"email": accounts[0][0], "code": reset_code, "new_password": "A-new-password-789"},
        )
        assert reset.status_code == 200, reset.text
        assert (await client.post("/auth/refresh", json={"refresh_token": old_pair["refresh_token"]})).status_code == 401
        assert (await client.get("/auth/session", headers={"Authorization": f"Bearer {old_pair['access_token']}"})).status_code == 401
        assert (await client.post("/auth/login", json={"email": accounts[0][0], "password": accounts[0][2]})).status_code == 401
        new_login = await client.post("/auth/login", json={"email": accounts[0][0], "password": "A-new-password-789"})
        assert new_login.status_code == 200, new_login.text
        other_login = await client.post("/auth/login", json={"email": accounts[1][0], "password": accounts[1][2]})
        assert other_login.status_code == 200, other_login.text
        await core_db.engine.dispose()
        persistent_login = await client.post("/auth/login", json={"email": accounts[0][0], "password": "A-new-password-789"})
        assert persistent_login.status_code == 200, persistent_login.text
