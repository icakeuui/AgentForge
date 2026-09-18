from __future__ import annotations

import os
import jwt
import smtplib
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.core.config import settings
from backend.core.database import Base
from backend.core.exceptions import AuthException, FlowException
from backend.models.orm import EmailVerificationCode, RefreshToken, TeamMember, User, UserCredential
from backend.services.account_service import account_service
from backend.services.email_service import EmailDeliveryError, email_service
from backend.services.password_service import password_service


def _build_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_password_hash_roundtrip():
    hashed = password_service.hash_password("StrongPass123")
    assert hashed != "StrongPass123"
    assert password_service.verify_password("StrongPass123", hashed) is True
    assert password_service.verify_password("wrong-password", hashed) is False


@pytest.mark.asyncio
async def test_password_hash_roundtrip_allows_short_passwords():
    hashed = password_service.hash_password("short")
    assert password_service.verify_password("short", hashed) is True


@pytest.mark.asyncio
async def test_local_registration_returns_dev_code_and_records_send_status(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    email_service.local_outbox.clear()
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            expires_in, retry_after, dev_code = await account_service.start_registration(session, email="user@example.com")
            assert expires_in == settings.EMAIL_VERIFICATION_CODE_TTL_SECONDS
            assert retry_after == settings.EMAIL_SEND_RATE_LIMIT_SECONDS
            assert dev_code is not None
        async with session_factory() as session:
            verification = (await session.execute(select(EmailVerificationCode))).scalar_one()
            assert verification.send_status == "SENT"
            assert verification.send_attempts == 1
            assert verification.last_send_error is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_dev_local_option_overrides_business_email_mode(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "smtp")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            _, _, dev_code = await account_service.start_registration(
                session,
                email="local-option@example.com",
                delivery_mode="local",
            )
            assert dev_code is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_dev_auto_mode_without_smtp_requires_local_option(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "auto")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            with pytest.raises(FlowException) as exc_info:
                await account_service.start_registration(session, email="dev-auto@example.com")
            assert exc_info.value.data["error_code"] == "EMAIL_PROVIDER_NOT_CONFIGURED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_local_option_is_dev_only(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "staging")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "smtp")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            with pytest.raises(FlowException) as exc_info:
                await account_service.start_registration(
                    session,
                    email="local-option-prod@example.com",
                    delivery_mode="local",
                )
            assert exc_info.value.data["error_code"] == "EMAIL_PROVIDER_NOT_CONFIGURED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_resend_rate_limit_and_old_code_invalidation(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    email_service.local_outbox.clear()
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            first_ttl = await account_service.start_registration(session, email="resend@example.com")
            assert first_ttl[0] == settings.EMAIL_VERIFICATION_CODE_TTL_SECONDS
            first_code = first_ttl[2]

        async with session_factory() as session:
            with pytest.raises(FlowException) as exc_info:
                await account_service.start_registration(session, email="resend@example.com")
            assert exc_info.value.data["error_code"] == "EMAIL_SEND_RATE_LIMITED"

        async with session_factory() as session:
            verification = (await session.execute(select(EmailVerificationCode))).scalar_one()
            verification.created_at = datetime.now(timezone.utc) - timedelta(seconds=settings.EMAIL_SEND_RATE_LIMIT_SECONDS + 1)
            verification.sent_at = verification.created_at
            await session.commit()

        async with session_factory() as session:
            second_ttl = await account_service.start_registration(session, email="resend@example.com")
            second_code = second_ttl[2]
            assert second_code is not None

        async with session_factory() as session:
            verification_rows = (await session.execute(select(EmailVerificationCode).order_by(EmailVerificationCode.created_at))).scalars().all()
            assert len(verification_rows) == 2
            assert verification_rows[0].invalidated_at is not None

        async with session_factory() as session:
            with pytest.raises(FlowException) as exc_info:
                await account_service.verify_registration(session, email="resend@example.com", code=first_code or "")
            assert exc_info.value.data["error_code"] == "VERIFICATION_CODE_INVALID"

        async with session_factory() as session:
            token = await account_service.verify_registration(session, email="resend@example.com", code=second_code or "")
            assert token
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_verification_attempts_are_capped(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            _, _, dev_code = await account_service.start_registration(session, email="attempts@example.com")
            assert dev_code is not None

        for attempt in range(5):
            async with session_factory() as session:
                with pytest.raises(FlowException) as exc_info:
                    await account_service.verify_registration(session, email="attempts@example.com", code="000000")
                assert exc_info.value.data["error_code"] == "VERIFICATION_CODE_INVALID"

        async with session_factory() as session:
            with pytest.raises(FlowException) as exc_info:
                await account_service.verify_registration(session, email="attempts@example.com", code="000000")
            assert exc_info.value.data["error_code"] == "VERIFICATION_CODE_ATTEMPTS_EXCEEDED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_prod_like_without_smtp_fails_and_records_status(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "staging")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "auto")
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            with pytest.raises(FlowException) as exc_info:
                await account_service.start_registration(session, email="prod@example.com")
            assert exc_info.value.data["error_code"] == "EMAIL_PROVIDER_NOT_CONFIGURED"

        async with session_factory() as session:
            verification = (await session.execute(select(EmailVerificationCode))).scalar_one()
            assert verification.send_status == "FAILED"
            assert verification.last_send_error == "Email delivery is not configured"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_registration_can_retry_after_send_failure_without_rate_limit(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "smtp")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "no-reply@example.test")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    attempts = 0

    async def fake_send_verification_code(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise EmailDeliveryError(
                error_code="EMAIL_SEND_FAILED",
                message="temporary failure",
                attempts=1,
                provider="smtp",
                retryable=False,
            )
        return type("SendResult", (), {"provider": "smtp", "attempts": 1, "dev_code": None})()

    monkeypatch.setattr(email_service, "send_verification_code", fake_send_verification_code)

    try:
        async with session_factory() as session:
            with pytest.raises(FlowException) as exc_info:
                await account_service.start_registration(session, email="retry@example.com")
            assert exc_info.value.data["error_code"] == "EMAIL_SEND_FAILED"

        async with session_factory() as session:
            expires_in, retry_after, dev_code = await account_service.start_registration(session, email="retry@example.com")
            assert expires_in == settings.EMAIL_VERIFICATION_CODE_TTL_SECONDS
            assert retry_after == settings.EMAIL_SEND_RATE_LIMIT_SECONDS
            assert dev_code is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_smtp_temporary_failure_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "smtp")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "no-reply@example.test")
    monkeypatch.setattr(settings, "EMAIL_SEND_RETRY_DELAYS_SECONDS", "0,0")
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)

    class FakeSMTP:
        attempts = 0

        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, username, password):
            pass

        def send_message(self, message):
            FakeSMTP.attempts += 1
            if FakeSMTP.attempts == 1:
                raise smtplib.SMTPServerDisconnected("temporary")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    result = await email_service.send_verification_code(to_email="smtp@example.com", code="123456", purpose="register")
    assert result.provider == "smtp"
    assert result.attempts == 2


@pytest.mark.asyncio
async def test_smtp_temporary_failure_exhausts_retries(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "smtp")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "no-reply@example.test")
    monkeypatch.setattr(settings, "EMAIL_SEND_MAX_RETRIES", 3)
    monkeypatch.setattr(settings, "EMAIL_SEND_RETRY_DELAYS_SECONDS", "0,0")
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, username, password):
            pass

        def send_message(self, message):
            raise smtplib.SMTPServerDisconnected("temporary")

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    with pytest.raises(EmailDeliveryError) as exc_info:
        await email_service.send_verification_code(to_email="smtp@example.com", code="123456", purpose="register")
    assert exc_info.value.error_code == "EMAIL_SEND_FAILED"
    assert exc_info.value.attempts == 3


@pytest.mark.asyncio
async def test_smtp_delivery_ignores_proxy_env_and_restores_it(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "smtp")
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "no-reply@example.test")
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)
    monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "no-reply@example.test")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "secret")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.example")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example")
    monkeypatch.setenv("ALL_PROXY", "socks5://proxy.example")
    monkeypatch.setenv("NO_PROXY", "localhost")
    monkeypatch.setenv("no_proxy", "localhost")

    seen_env: dict[str, str | None] = {}

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            seen_env["HTTP_PROXY"] = os.environ.get("HTTP_PROXY")
            seen_env["HTTPS_PROXY"] = os.environ.get("HTTPS_PROXY")
            seen_env["ALL_PROXY"] = os.environ.get("ALL_PROXY")
            seen_env["NO_PROXY"] = os.environ.get("NO_PROXY")
            seen_env["no_proxy"] = os.environ.get("no_proxy")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self):
            pass

        def login(self, username, password):
            pass

        def send_message(self, message):
            pass

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    result = await email_service.send_verification_code(
        to_email="direct@example.com",
        code="123456",
        purpose="register",
    )
    assert result.provider == "smtp"
    assert result.attempts == 1
    assert seen_env == {
        "HTTP_PROXY": None,
        "HTTPS_PROXY": None,
        "ALL_PROXY": None,
        "NO_PROXY": "smtp.example.test",
        "no_proxy": "smtp.example.test",
    }
    assert os.environ["HTTP_PROXY"] == "http://proxy.example"
    assert os.environ["HTTPS_PROXY"] == "http://proxy.example"
    assert os.environ["ALL_PROXY"] == "socks5://proxy.example"
    assert os.environ["NO_PROXY"] == "localhost"
    assert os.environ["no_proxy"] == "localhost"


@pytest.mark.asyncio
async def test_complete_registration_login_and_refresh_jwt_v2(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            _, _, dev_code = await account_service.start_registration(session, email="alice@example.com")
            registration_token = await account_service.verify_registration(session, email="alice@example.com", code=dev_code or "")

        async with session_factory() as session:
            token_pair = await account_service.complete_registration(
                session,
                email="alice@example.com",
                registration_token=registration_token,
                password="abc123",
                confirm_password="abc123",
                display_name="Alice",
                avatar_url="https://example.com/avatar.png",
            )
            payload = jwt.decode(token_pair.access_token, settings.JWT_SECRET, algorithms=["HS256"])
            assert payload["ver"] == 2
            assert payload["sub"] == token_pair.user.user_id
            assert payload["user_id"] == token_pair.user.user_id
            assert payload["search_id"] == str(token_pair.user.search_id)
            assert payload["email"] == "alice@example.com"
            assert payload["email_verified"] is True
            assert token_pair.user.team_id is not None
            assert token_pair.user.role == "owner"

        async with session_factory() as session:
            login_pair = await account_service.login(session, email="alice@example.com", password="abc123")
            assert login_pair.user.user_id == token_pair.user.user_id

        async with session_factory() as session:
            refreshed = await account_service.refresh(session, refresh_token=token_pair.refresh_token)
            assert refreshed.refresh_token != token_pair.refresh_token
            token_record = (await session.execute(select(RefreshToken))).scalars().all()
            assert len(token_record) >= 2
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_disabled_user_cannot_login(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            _, _, dev_code = await account_service.start_registration(session, email="disabled@example.com")
            registration_token = await account_service.verify_registration(session, email="disabled@example.com", code=dev_code or "")
            pair = await account_service.complete_registration(
                session,
                email="disabled@example.com",
                registration_token=registration_token,
                password="StrongPass123",
                confirm_password="StrongPass123",
                display_name="Disabled",
                avatar_url=None,
            )

        async with session_factory() as session:
            user = await session.get(User, pair.user.user_id)
            assert user is not None
            user.status = "DISABLED"
            await session.commit()

        async with session_factory() as session:
            with pytest.raises(FlowException) as exc_info:
                await account_service.login(session, email="disabled@example.com", password="StrongPass123")
            assert exc_info.value.data["error_code"] == "ACCOUNT_DISABLED"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reset_password_allows_short_password(monkeypatch):
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "local")
    engine, session_factory = _build_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with session_factory() as session:
            _, _, dev_code = await account_service.start_registration(session, email="reset-short@example.com")
            registration_token = await account_service.verify_registration(session, email="reset-short@example.com", code=dev_code or "")
            await account_service.complete_registration(
                session,
                email="reset-short@example.com",
                registration_token=registration_token,
                password="abc123",
                confirm_password="abc123",
                display_name="Reset",
                avatar_url=None,
            )

        async with session_factory() as session:
            _, dev_reset_code = await account_service.start_password_reset(session, email="reset-short@example.com")
            assert dev_reset_code is not None

        async with session_factory() as session:
            await account_service.reset_password(
                session,
                email="reset-short@example.com",
                code=dev_reset_code or "",
                new_password="12345",
            )

        async with session_factory() as session:
            login_pair = await account_service.login(session, email="reset-short@example.com", password="12345")
            assert login_pair.user.email == "reset-short@example.com"
    finally:
        await engine.dispose()
