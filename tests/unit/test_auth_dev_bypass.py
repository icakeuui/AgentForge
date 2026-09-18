import jwt
import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from backend.api.dependencies import resolve_auth_context
from backend.core.config import settings
from backend.core.exceptions import AuthException


def _request(path: str = "/api/v1/agents"):
    return SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path=path),
        state=SimpleNamespace(request_id="req-dev-bypass"),
    )


@pytest.mark.asyncio
async def test_dev_bypass_enabled_in_dev_returns_fixed_auth_context(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_ENABLED", True)
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setattr(settings, "AUTH_DEV_USER_ID", "dev-fixed-user")
    monkeypatch.setattr(settings, "AUTH_DEV_TEAM_ID", "00000000-0000-0000-0000-000000000001")
    monkeypatch.setattr(settings, "AUTH_DEV_ROLE", "developer")

    auth = await resolve_auth_context(request=_request(), authorization=None)
    assert auth.auth_mode == "dev_bypass"
    assert auth.user_id == "dev-fixed-user"
    assert auth.team_id == "00000000-0000-0000-0000-000000000001"
    assert auth.is_dev is True


@pytest.mark.asyncio
async def test_dev_bypass_enabled_in_non_dev_fails_fast(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_ENABLED", True)
    monkeypatch.setattr(settings, "ENV", "production")

    with pytest.raises(AuthException):
        await resolve_auth_context(request=_request(), authorization=None)


@pytest.mark.asyncio
async def test_dev_bypass_cannot_switch_user_via_jwt_or_headers(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_ENABLED", True)
    monkeypatch.setattr(settings, "ENV", "local")
    monkeypatch.setattr(settings, "AUTH_DEV_USER_ID", "dev-fixed-user")
    monkeypatch.setattr(settings, "AUTH_DEV_TEAM_ID", "00000000-0000-0000-0000-000000000001")

    payload = {
        "sub": "attacker-user",
        "team_id": "00000000-0000-0000-0000-000000000002",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    auth = await resolve_auth_context(request=_request(), authorization=f"Bearer {token}")
    assert auth.user_id == "dev-fixed-user"
    assert auth.team_id == "00000000-0000-0000-0000-000000000001"
    assert auth.auth_mode == "dev_bypass"


@pytest.mark.asyncio
async def test_jwt_branch_still_works_when_bypass_disabled(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DEV_BYPASS_ENABLED", False)
    monkeypatch.setattr(settings, "ENV", "development")

    payload = {
        "sub": "user1",
        "team_id": "00000000-0000-0000-0000-000000000001",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    auth = await resolve_auth_context(request=_request(), authorization=f"Bearer {token}")
    assert auth.auth_mode == "jwt"
    assert auth.user_id == "user1"
