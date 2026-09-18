from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from tests.e2e.smtp_capture_server import SmtpCaptureServer


@pytest.fixture
def smtp_capture_server():
    server = SmtpCaptureServer()
    server.start()
    try:
        yield server
    finally:
        server.stop()


def _configure_smtp(monkeypatch: pytest.MonkeyPatch, smtp_capture_server: SmtpCaptureServer) -> None:
    monkeypatch.setattr(settings, "ENV", "dev")
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_MODE", "smtp")
    monkeypatch.setattr(settings, "SMTP_HOST", smtp_capture_server.host)
    monkeypatch.setattr(settings, "SMTP_PORT", smtp_capture_server.smtp_port)
    monkeypatch.setattr(settings, "SMTP_USERNAME", "")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "no-reply@agentforge.test")
    monkeypatch.setattr(settings, "SMTP_FROM_NAME", "AgentForge E2E")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", False)
    monkeypatch.setattr(settings, "SMTP_USE_SSL", False)


def _register_user_via_smtp(
    client: TestClient,
    smtp_capture_server: SmtpCaptureServer,
    *,
    email: str,
    password: str,
    display_name: str,
) -> None:
    start_response = client.post("/auth/register/start", json={"email": email})
    assert start_response.status_code == 200
    start_payload = start_response.json()["data"]
    assert start_payload["dev_code"] is None

    code = smtp_capture_server.wait_for_code(
        recipient=email,
        subject_contains="email verification",
        timeout=5.0,
    )
    verify_response = client.post("/auth/register/verify", json={"email": email, "code": code})
    assert verify_response.status_code == 200
    registration_token = verify_response.json()["data"]["registration_token"]

    complete_response = client.post(
        "/auth/register/complete",
        json={
            "email": email,
            "registration_token": registration_token,
            "password": password,
            "confirm_password": password,
            "display_name": display_name,
            "avatar_url": None,
        },
    )
    assert complete_response.status_code == 200


def test_registration_flow_uses_smtp_end_to_end(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    smtp_capture_server: SmtpCaptureServer,
):
    _configure_smtp(monkeypatch, smtp_capture_server)
    email = "smtp-register@example.com"
    password = "StrongPass123!"

    _register_user_via_smtp(
        client,
        smtp_capture_server,
        email=email,
        password=password,
        display_name="SMTP Register",
    )

    messages = smtp_capture_server.store.list(recipient=email)
    assert len(messages) == 1
    assert messages[0].subject == "AgentForge email verification"
    assert "Your AgentForge verification code is" in messages[0].body

    login_response = client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    login_payload = login_response.json()["data"]
    assert login_payload["user"]["email"] == email
    assert login_payload["access_token"]
    assert login_payload["refresh_token"]


def test_password_reset_flow_uses_smtp_end_to_end(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    smtp_capture_server: SmtpCaptureServer,
):
    _configure_smtp(monkeypatch, smtp_capture_server)
    email = "smtp-reset@example.com"
    old_password = "OldPass123!"
    new_password = "NewPass456!"

    _register_user_via_smtp(
        client,
        smtp_capture_server,
        email=email,
        password=old_password,
        display_name="SMTP Reset",
    )
    smtp_capture_server.store.clear()

    forgot_response = client.post("/auth/password/forgot", json={"email": email})
    assert forgot_response.status_code == 200
    forgot_payload = forgot_response.json()["data"]
    assert forgot_payload["dev_code"] is None

    reset_code = smtp_capture_server.wait_for_code(
        recipient=email,
        subject_contains="password reset",
        timeout=5.0,
    )
    reset_response = client.post(
        "/auth/password/reset",
        json={"email": email, "code": reset_code, "new_password": new_password},
    )
    assert reset_response.status_code == 200

    old_login = client.post("/auth/login", json={"email": email, "password": old_password})
    assert old_login.status_code == 401

    new_login = client.post("/auth/login", json={"email": email, "password": new_password})
    assert new_login.status_code == 200
    assert new_login.json()["data"]["user"]["email"] == email
