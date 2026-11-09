"""Avatar registration checks against the isolated on-disk test database."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.core.config import settings
from backend.main import app
from backend.services.account_service import account_service
import backend.services.avatar_storage_service as avatar_storage_module


@pytest.mark.asyncio
async def test_registration_avatar_persists_and_is_isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    monkeypatch.setattr(settings, "AVATAR_STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "AVATAR_PUBLIC_BASE_URL", "")
    monkeypatch.setattr(avatar_storage_module, "LOCAL_AVATAR_UPLOAD_DIR", tmp_path / "avatars")
    codes = iter(("111111", "222222", "333333"))
    monkeypatch.setattr(account_service, "_new_code", lambda: next(codes))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        avatar_urls = []
        for index in (1, 2):
            email = f"avatar-test-{index}@example.com"
            image = b"\x89PNG\r\n\x1a\n" + bytes([index]) * 16
            uploaded = await client.post("/auth/avatar/upload", files={"file": ("avatar.png", image, "image/png")})
            assert uploaded.status_code == 200, uploaded.text
            avatar_url = uploaded.json()["data"]["avatar_url"]
            avatar_urls.append(avatar_url)
            assert avatar_url.startswith("http://test/uploads/avatars/")
            assert (tmp_path / "avatars" / avatar_url.rsplit("/", 1)[-1]).read_bytes() == image

            started = await client.post("/auth/register/start", json={"email": email, "delivery_mode": "local"})
            assert started.status_code == 200, started.text
            verified = await client.post("/auth/register/verify", json={"email": email, "code": started.json()["data"]["dev_code"]})
            assert verified.status_code == 200, verified.text
            password = f"Avatar-Test-{index}-123"
            completed = await client.post("/auth/register/complete", json={
                "email": email,
                "registration_token": verified.json()["data"]["registration_token"],
                "password": password,
                "confirm_password": password,
                "display_name": f"Avatar User {index}",
                "avatar_url": avatar_url,
            })
            assert completed.status_code == 200, completed.text
            assert completed.json()["data"]["user"]["avatar_url"] == avatar_url

            token = completed.json()["data"]["access_token"]
            profile = await client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})
            assert profile.status_code == 200, profile.text
            assert profile.json()["data"]["avatar_url"] == avatar_url

            logged_in = await client.post("/auth/login", json={"email": email, "password": password})
            assert logged_in.status_code == 200, logged_in.text
            assert logged_in.json()["data"]["user"]["avatar_url"] == avatar_url

        assert avatar_urls[0] != avatar_urls[1]

        email = "avatar-test-default@example.com"
        started = await client.post("/auth/register/start", json={"email": email, "delivery_mode": "local"})
        verified = await client.post("/auth/register/verify", json={"email": email, "code": started.json()["data"]["dev_code"]})
        password = "Avatar-Test-Default-123"
        completed = await client.post("/auth/register/complete", json={
            "email": email,
            "registration_token": verified.json()["data"]["registration_token"],
            "password": password,
            "confirm_password": password,
            "display_name": "Default Avatar User",
            "avatar_url": None,
        })
        assert completed.status_code == 200, completed.text
        assert completed.json()["data"]["user"]["avatar_url"] is None
