import pytest
import jwt
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from fastapi.testclient import TestClient

from backend.api.dependencies import resolve_auth_context, verify_team_permission
from backend.main import app
from backend.core.config import settings
from backend.core.exceptions import AuthException, PermissionException
from backend.models.constants import ResponseCode
from backend.models.schemas import AuthContext


client = TestClient(app, raise_server_exceptions=False)


def _request_with_request_id(request_id: str = "req-test"):
    return SimpleNamespace(
        method="GET",
        url=SimpleNamespace(path="/test"),
        state=SimpleNamespace(request_id=request_id),
    )

@pytest.mark.asyncio
async def test_resolve_auth_context_no_token():
    with pytest.raises(AuthException) as exc:
        await resolve_auth_context(request=_request_with_request_id(), authorization=None)
    assert exc.value.code == ResponseCode.AUTH_REQUIRED

@pytest.mark.asyncio
async def test_resolve_auth_context_invalid_token():
    with pytest.raises(AuthException) as exc:
        await resolve_auth_context(request=_request_with_request_id(), authorization="Bearer invalid.token.here")
    assert exc.value.code == ResponseCode.TOKEN_INVALID

@pytest.mark.asyncio
async def test_resolve_auth_context_expired_token():
    payload = {
        "user_id": "user1",
        "team_id": "team1",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    
    with pytest.raises(AuthException) as exc:
        await resolve_auth_context(request=_request_with_request_id(), authorization=f"Bearer {token}")
    assert exc.value.code == ResponseCode.TOKEN_EXPIRED

@pytest.mark.asyncio
async def test_resolve_auth_context_valid_token():
    payload = {
        "user_id": "user1",
        "team_id": "team1",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    
    auth = await resolve_auth_context(request=_request_with_request_id(), authorization=f"Bearer {token}")
    assert auth.user_id == "user1"
    assert auth.team_id == "team1"
    assert auth.auth_mode == "jwt"

@pytest.mark.asyncio
async def test_verify_team_permission():
    auth = AuthContext(
        user_id="user1",
        team_id="team1",
        auth_mode="jwt",
        request_id="req-test",
    )
    class MockTeam:
        status = "ACTIVE"
    
    # Same team -> OK
    with patch("backend.api.dependencies.competition_manager_service.get_team", new_callable=AsyncMock) as mock_get_team:
        mock_get_team.return_value = MockTeam()
        res = await verify_team_permission("team1", auth=auth)
    assert res == "team1"
    
    # Different team -> Error
    with patch("backend.api.dependencies.competition_manager_service.get_team", new_callable=AsyncMock) as mock_get_team:
        mock_get_team.return_value = MockTeam()
        with pytest.raises(PermissionException) as exc:
            await verify_team_permission("team2", auth=auth)
    assert exc.value.code == ResponseCode.TEAM_FORBIDDEN


def test_upload_avatar_returns_public_url(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.services.avatar_storage_service.LOCAL_AVATAR_UPLOAD_DIR", tmp_path / "avatars")
    monkeypatch.setattr(settings, "AVATAR_STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "AVATAR_PUBLIC_BASE_URL", "")

    response = client.post(
        "/auth/avatar/upload",
        files={"file": ("avatar.png", b"avatar-bytes", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    avatar_url = payload["data"]["avatar_url"]
    assert avatar_url.startswith("http://testserver/uploads/avatars/")
    stored = list((tmp_path / "avatars").iterdir())
    assert len(stored) == 1
    assert stored[0].read_bytes() == b"avatar-bytes"


def test_upload_avatar_returns_object_storage_url(monkeypatch):
    monkeypatch.setattr(settings, "AVATAR_STORAGE_PROVIDER", "s3")
    monkeypatch.setattr(settings, "OBJECT_STORAGE_ENDPOINT", "https://s3.example.test")
    monkeypatch.setattr(settings, "OBJECT_STORAGE_BUCKET", "avatars-bucket")
    monkeypatch.setattr(settings, "OBJECT_STORAGE_ACCESS_KEY", "access")
    monkeypatch.setattr(settings, "OBJECT_STORAGE_SECRET_KEY", "secret")
    monkeypatch.setattr(settings, "OBJECT_STORAGE_PUBLIC_BASE_URL", "https://cdn.example.test")
    monkeypatch.setattr(settings, "OBJECT_STORAGE_PUBLIC_READ", True)

    captured: dict[str, object] = {}

    class FakeClient:
        def put_object(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("backend.services.avatar_storage_service.avatar_storage_service._create_s3_client", lambda: FakeClient())

    response = client.post(
        "/auth/avatar/upload",
        files={"file": ("avatar.png", b"avatar-bytes", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    avatar_url = payload["data"]["avatar_url"]
    assert avatar_url.startswith("https://cdn.example.test/avatars/")
    assert captured["Bucket"] == "avatars-bucket"
    assert captured["Body"] == b"avatar-bytes"
    assert captured["ContentType"] == "image/png"
