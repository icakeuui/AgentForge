from __future__ import annotations

import asyncio
import contextlib
import os
import smtplib
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any

from backend.core.config import settings
from backend.core.logging import logger


@dataclass(slots=True)
class EmailDeliveryResult:
    provider: str
    attempts: int
    dev_code: str | None = None


class EmailDeliveryError(Exception):
    def __init__(
        self,
        *,
        error_code: str,
        message: str,
        attempts: int = 0,
        provider: str = "smtp",
        retryable: bool = False,
        stage: str | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.attempts = attempts
        self.provider = provider
        self.retryable = retryable
        self.stage = stage
        self.detail = detail or message


class EmailService:
    _proxy_env_keys = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")

    def __init__(self) -> None:
        self.local_outbox: list[dict[str, Any]] = []
        self._proxy_lock = threading.Lock()

    async def send_verification_code(
        self,
        *,
        to_email: str,
        code: str,
        purpose: str,
        delivery_mode: str | None = None,
    ) -> EmailDeliveryResult:
        subject = "AgentForge email verification"
        if purpose == "reset_password":
            subject = "AgentForge password reset"
        body = (
            f"Your AgentForge verification code is: {code}\n\n"
            f"This code expires in a few minutes. If you did not request it, you can ignore this email."
        )
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            code=code,
            purpose=purpose,
            delivery_mode=delivery_mode,
        )

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        code: str | None = None,
        purpose: str | None = None,
        delivery_mode: str | None = None,
    ) -> EmailDeliveryResult:
        mode = (delivery_mode or settings.EMAIL_DELIVERY_MODE).strip().lower()
        smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)

        if mode == "local" and not settings.is_dev_env:
            raise EmailDeliveryError(
                error_code="EMAIL_PROVIDER_NOT_CONFIGURED",
                message="Local email delivery is not allowed in this environment",
                attempts=0,
                provider="local",
                retryable=False,
            )

        if mode == "local":
            self.local_outbox.append(
                {
                    "to_email": to_email,
                    "subject": subject,
                    "body": body,
                    "code": code,
                    "purpose": purpose,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.bind(resource_type="email", resource_id=to_email).info("local email delivery log")
            return EmailDeliveryResult(provider="local", attempts=1, dev_code=code)

        if mode not in {"auto", "smtp"}:
            raise EmailDeliveryError(
                error_code="EMAIL_PROVIDER_NOT_CONFIGURED",
                message=f"Unsupported email delivery mode: {mode}",
                attempts=0,
                provider="smtp",
                retryable=False,
            )

        if not smtp_configured:
            raise EmailDeliveryError(
                error_code="EMAIL_PROVIDER_NOT_CONFIGURED",
                message="Email delivery is not configured",
                attempts=0,
                provider="smtp",
                retryable=False,
            )

        # QQ SMTP requires the full mailbox address and a generated SMTP
        # authorization code. Fail with a configuration error before opening
        # an unauthenticated session when either value is missing.
        if settings.SMTP_HOST.lower() in {"smtp.qq.com", "smtp.exmail.qq.com"} and (
            not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD
        ):
            raise EmailDeliveryError(
                error_code="EMAIL_PROVIDER_NOT_CONFIGURED",
                message="QQ SMTP requires SMTP_USERNAME and an SMTP authorization code in SMTP_PASSWORD",
                attempts=0,
                provider="smtp",
                retryable=False,
                stage="config",
            )

        message = EmailMessage()
        from_header = settings.SMTP_FROM_EMAIL
        if settings.SMTP_FROM_NAME:
            from_header = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        message["From"] = from_header
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        last_error: EmailDeliveryError | None = None
        retry_delays = self._retry_delays()
        for attempt in range(1, settings.EMAIL_SEND_MAX_RETRIES + 1):
            try:
                await asyncio.to_thread(self._send_message, message)
                return EmailDeliveryResult(provider="smtp", attempts=attempt, dev_code=None)
            except EmailDeliveryError as exc:
                if not exc.attempts:
                    exc.attempts = attempt
                last_error = exc
                logger.bind(resource_type="email", resource_id=to_email).warning(
                    f"smtp attempt failed log: attempt={attempt} stage={exc.stage or 'unknown'} "
                    f"retryable={exc.retryable} detail={exc.detail}"
                )
                if settings.is_dev_env and exc.stage == "connect":
                    # In local/e2e workflows a dead outbound SMTP route is not going to
                    # recover within the next retry window, and fast failure is much
                    # easier to troubleshoot than waiting through every retry.
                    break
                if not exc.retryable or attempt >= settings.EMAIL_SEND_MAX_RETRIES:
                    break
            except Exception as exc:
                last_error = self._classify_exception(exc, attempts=attempt)
                logger.bind(resource_type="email", resource_id=to_email).warning(
                    f"smtp attempt failed log: attempt={attempt} stage={last_error.stage or 'unknown'} "
                    f"retryable={last_error.retryable} detail={last_error.detail}"
                )
                if settings.is_dev_env and last_error.stage == "connect":
                    break
                if not last_error.retryable or attempt >= settings.EMAIL_SEND_MAX_RETRIES:
                    break

            delay_index = min(attempt - 1, len(retry_delays) - 1)
            if delay_index >= 0:
                await asyncio.sleep(retry_delays[delay_index])

        if last_error is not None:
            logger.bind(resource_type="email", resource_id="smtp").error(
                f"smtp send failed log: provider error type={type(last_error).__name__} "
                f"code={last_error.error_code} stage={last_error.stage or 'unknown'} detail={last_error.detail}"
            )
            raise last_error

        raise EmailDeliveryError(
            error_code="EMAIL_SEND_FAILED",
            message="Unable to send verification email",
            attempts=settings.EMAIL_SEND_MAX_RETRIES,
            provider="smtp",
            retryable=False,
        )

    def _send_message(self, message: EmailMessage) -> None:
        try:
            with self._direct_domestic_network(settings.SMTP_HOST):
                smtp_class = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
                with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as smtp:
                    try:
                        smtp.ehlo()
                    except Exception as exc:
                        raise self._stage_error("ehlo", exc)
                    if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                        try:
                            smtp.starttls()
                            # After STARTTLS, SMTP clients should identify again.
                            smtp.ehlo()
                        except Exception as exc:
                            raise self._stage_error("starttls", exc)
                    if settings.SMTP_USERNAME:
                        try:
                            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                        except Exception as exc:
                            raise self._stage_error("login", exc)
                    try:
                        smtp.send_message(message)
                    except Exception as exc:
                        raise self._stage_error("send_message", exc)
        except Exception as exc:
            if isinstance(exc, EmailDeliveryError):
                raise exc
            raise self._stage_error("connect", exc) from exc

    def _stage_error(self, stage: str, exc: Exception) -> EmailDeliveryError:
        classified = self._classify_exception(exc)
        classified.stage = stage
        if stage == "connect":
            classified.detail = (
                f"Unable to connect to SMTP server {settings.SMTP_HOST}:{settings.SMTP_PORT} "
                f"({type(exc).__name__}: {exc})"
            )
        else:
            classified.detail = f"{stage}: {type(exc).__name__}: {exc}"
        classified.message = classified.detail
        return classified

    @contextlib.contextmanager
    def _direct_domestic_network(self, host: str):
        # SMTP uses raw sockets already; this guard explicitly strips proxy env vars so
        # the mail path stays direct and domestic for the duration of the send.
        with self._proxy_lock:
            original_values = {key: os.environ.get(key) for key in self._proxy_env_keys}
            original_no_proxy = os.environ.get("NO_PROXY")
            original_no_proxy_lower = os.environ.get("no_proxy")
            try:
                for key in self._proxy_env_keys:
                    os.environ.pop(key, None)
                os.environ["NO_PROXY"] = host
                os.environ["no_proxy"] = host
                yield
            finally:
                for key, value in original_values.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                if original_no_proxy is None:
                    os.environ.pop("NO_PROXY", None)
                else:
                    os.environ["NO_PROXY"] = original_no_proxy
                if original_no_proxy_lower is None:
                    os.environ.pop("no_proxy", None)
                else:
                    os.environ["no_proxy"] = original_no_proxy_lower

    def _retry_delays(self) -> list[float]:
        delays: list[float] = []
        for raw in settings.EMAIL_SEND_RETRY_DELAYS_SECONDS.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                delays.append(float(raw))
            except ValueError:
                continue
        return delays or [1.0, 3.0]

    def _classify_exception(self, exc: Exception, *, attempts: int = 0) -> EmailDeliveryError:
        if isinstance(exc, EmailDeliveryError):
            return exc
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            return EmailDeliveryError(
                error_code="EMAIL_SEND_FAILED",
                message="SMTP authentication failed",
                attempts=attempts,
                provider="smtp",
                retryable=False,
                stage="login",
            )
        if isinstance(exc, smtplib.SMTPRecipientsRefused):
            return EmailDeliveryError(
                error_code="EMAIL_SEND_FAILED",
                message="Recipient address rejected",
                attempts=attempts,
                provider="smtp",
                retryable=False,
                stage="send_message",
            )
        if isinstance(exc, smtplib.SMTPSenderRefused):
            return EmailDeliveryError(
                error_code="EMAIL_SEND_FAILED",
                message="Sender address rejected",
                attempts=attempts,
                provider="smtp",
                retryable=False,
                stage="send_message",
            )
        if isinstance(exc, smtplib.SMTPDataError):
            retryable = 400 <= getattr(exc, "smtp_code", 0) < 500
            return EmailDeliveryError(
                error_code="EMAIL_SEND_FAILED",
                message=f"SMTP data error: {getattr(exc, 'smtp_code', 'unknown')}",
                attempts=attempts,
                provider="smtp",
                retryable=retryable,
                stage="send_message",
            )
        if isinstance(exc, smtplib.SMTPResponseException):
            retryable = 400 <= getattr(exc, "smtp_code", 0) < 500
            return EmailDeliveryError(
                error_code="EMAIL_SEND_FAILED",
                message=f"SMTP response error: {getattr(exc, 'smtp_code', 'unknown')}",
                attempts=attempts,
                provider="smtp",
                retryable=retryable,
                stage="smtp_response",
            )
        if isinstance(exc, (TimeoutError, OSError, smtplib.SMTPServerDisconnected)):
            return EmailDeliveryError(
                error_code="EMAIL_SEND_FAILED",
                message=type(exc).__name__,
                attempts=attempts,
                provider="smtp",
                retryable=True,
                detail=f"{type(exc).__name__}: {exc}",
            )
        return EmailDeliveryError(
            error_code="EMAIL_SEND_FAILED",
            message=type(exc).__name__,
            attempts=attempts,
            provider="smtp",
            retryable=False,
            detail=f"{type(exc).__name__}: {exc}",
        )

    def latest_local_code(self, *, email: str, purpose: str) -> str | None:
        for message in reversed(self.local_outbox):
            if message.get("to_email") == email and message.get("purpose") == purpose:
                code = message.get("code")
                return code if isinstance(code, str) else None
        return None


email_service = EmailService()
