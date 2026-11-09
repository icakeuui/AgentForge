"""Registration-code regression checks against an isolated on-disk SQLite database."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.core import database as core_db
from backend.core.config import settings
from backend.main import app
from backend.models.orm import EmailVerificationCode
from backend.services.account_service import account_service
from backend.services.email_service import email_service


@pytest.mark.asyncio
async def test_registration_code_lock_resend_expiry_and_completion(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    generated_codes = iter(("111111", "222222", "333333", "444444", "555555"))
    monkeypatch.setattr(account_service, "_new_code", lambda: next(generated_codes))

    async def latest_code(email: str) -> EmailVerificationCode:
        async with core_db.AsyncSessionLocal() as session:
            result = await session.execute(
                select(EmailVerificationCode)
                .where(EmailVerificationCode.email == email, EmailVerificationCode.purpose == "register")
                .order_by(EmailVerificationCode.created_at.desc(), EmailVerificationCode.sent_at.desc())
            )
            return result.scalars().first()

    async def age_send(email: str) -> None:
        async with core_db.AsyncSessionLocal() as session:
            record = (await session.execute(
                select(EmailVerificationCode)
                .where(EmailVerificationCode.email == email, EmailVerificationCode.invalidated_at.is_(None))
                .order_by(EmailVerificationCode.created_at.desc(), EmailVerificationCode.sent_at.desc())
            )).scalars().first()
            assert record is not None
            record.sent_at = datetime.now(timezone.utc) - timedelta(seconds=settings.EMAIL_SEND_RATE_LIMIT_SECONDS + 1)
            await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        a = "agentforge-code-a@qq.com"
        b = "agentforge-code-b@qq.com"
        c = "agentforge-code-expired@qq.com"

        sent_a = await client.post("/auth/register/start", json={"email": a, "delivery_mode": "local"})
        assert sent_a.status_code == 200 and sent_a.json()["data"]["dev_code"] == "111111"
        assert "expires in 10 minutes" in email_service.local_outbox[-1]["body"]
        assert (await latest_code(a)).verification_attempts == 0

        for attempt in range(1, 6):
            wrong = await client.post("/auth/register/verify", json={"email": a, "code": "999999"})
            assert wrong.status_code == 400
            expected_error = "VERIFICATION_CODE_ATTEMPTS_EXCEEDED" if attempt == 5 else "VERIFICATION_CODE_INVALID"
            assert wrong.json()["data"]["error_code"] == expected_error
        locked = await client.post("/auth/register/verify", json={"email": a, "code": "111111"})
        assert locked.status_code == 400
        assert locked.json()["data"]["error_code"] == "VERIFICATION_CODE_ATTEMPTS_EXCEEDED"
        assert (await latest_code(a)).verification_attempts == 5

        sent_b = await client.post("/auth/register/start", json={"email": b, "delivery_mode": "local"})
        assert sent_b.status_code == 200 and sent_b.json()["data"]["dev_code"] == "222222"
        verified_b = await client.post("/auth/register/verify", json={"email": b, "code": "222222"})
        assert verified_b.status_code == 200

        rate_limited = await client.post("/auth/register/start", json={"email": a, "delivery_mode": "local"})
        assert rate_limited.status_code == 429
        await age_send(a)
        resent_a = await client.post("/auth/register/start", json={"email": a, "delivery_mode": "local"})
        assert resent_a.status_code == 200 and resent_a.json()["data"]["dev_code"] == "333333"
        assert (await latest_code(a)).verification_attempts == 0
        old_code = await client.post("/auth/register/verify", json={"email": a, "code": "111111"})
        assert old_code.status_code == 400 and old_code.json()["data"]["error_code"] == "VERIFICATION_CODE_INVALID"
        formatted_code = await client.post("/auth/register/verify", json={"email": a, "code": " 3\u200b33333 "})
        assert formatted_code.status_code == 200, formatted_code.text

        # Abandon the verified form, then start again as after a browser refresh.
        restarted_a = await client.post("/auth/register/start", json={"email": a, "delivery_mode": "local"})
        assert restarted_a.status_code == 200 and restarted_a.json()["data"]["dev_code"] == "444444"
        verified_a = await client.post("/auth/register/verify", json={"email": a, "code": "444444"})
        assert verified_a.status_code == 200

        for email, token, password in (
            (a, verified_a.json()["data"]["registration_token"], "Password-A-123"),
            (b, verified_b.json()["data"]["registration_token"], "Password-B-456"),
        ):
            completed = await client.post("/auth/register/complete", json={
                "email": email,
                "registration_token": token,
                "password": password,
                "confirm_password": password,
                "display_name": email.split("@")[0],
            })
            assert completed.status_code == 200, completed.text
            logged_in = await client.post("/auth/login", json={"email": email, "password": password})
            assert logged_in.status_code == 200 and logged_in.json()["data"]["user"]["email"] == email
            already_registered = await client.post("/auth/register/start", json={"email": email, "delivery_mode": "local"})
            assert already_registered.status_code == 409

        sent_c = await client.post("/auth/register/start", json={"email": c, "delivery_mode": "local"})
        assert sent_c.status_code == 200 and sent_c.json()["data"]["dev_code"] == "555555"
        async with core_db.AsyncSessionLocal() as session:
            record = (await session.execute(select(EmailVerificationCode).where(EmailVerificationCode.email == c))).scalar_one()
            record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()
        expired = await client.post("/auth/register/verify", json={"email": c, "code": "555555"})
        assert expired.status_code == 400 and expired.json()["data"]["error_code"] == "VERIFICATION_CODE_EXPIRED"
