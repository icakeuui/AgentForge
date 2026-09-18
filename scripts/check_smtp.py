from __future__ import annotations

import argparse
import json
import smtplib
import socket
import sys
from email.message import EmailMessage
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings


def emit(stage: str, ok: bool, **extra: object) -> None:
    payload = {"stage": stage, "ok": ok, **extra}
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SMTP connectivity step by step")
    parser.add_argument("--recipient", help="Optional recipient for a real send test")
    parser.add_argument("--subject", default="AgentForge SMTP diagnostic")
    parser.add_argument("--body", default="AgentForge SMTP diagnostic mail")
    args = parser.parse_args()

    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    timeout = settings.SMTP_TIMEOUT_SECONDS

    try:
        resolved = socket.gethostbyname(host)
        emit("resolve", True, host=host, resolved_ip=resolved)
    except Exception as exc:
        emit("resolve", False, host=host, error=f"{type(exc).__name__}: {exc}")
        return 1

    smtp_class = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    smtp: smtplib.SMTP | smtplib.SMTP_SSL | None = None
    try:
        smtp = smtp_class(host, port, timeout=timeout)
        peer = smtp.sock.getpeername() if smtp.sock else None
        emit("connect", True, host=host, port=port, peer=peer)

        ehlo_code, ehlo_msg = smtp.ehlo()
        emit("ehlo", ehlo_code == 250, code=ehlo_code, message=ehlo_msg.decode("utf-8", "replace"))
        if ehlo_code != 250:
            return 1

        if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
            tls_code, tls_msg = smtp.starttls()
            emit("starttls", tls_code == 220, code=tls_code, message=tls_msg.decode("utf-8", "replace"))
            if tls_code != 220:
                return 1
            ehlo2_code, ehlo2_msg = smtp.ehlo()
            emit("ehlo_after_starttls", ehlo2_code == 250, code=ehlo2_code, message=ehlo2_msg.decode("utf-8", "replace"))
            if ehlo2_code != 250:
                return 1

        if settings.SMTP_USERNAME:
            login_code, login_msg = smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            emit("login", login_code == 235, code=login_code, message=login_msg.decode("utf-8", "replace"))
            if login_code != 235:
                return 1

        if args.recipient:
            message = EmailMessage()
            from_header = settings.SMTP_FROM_EMAIL
            if settings.SMTP_FROM_NAME:
                from_header = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["From"] = from_header
            message["To"] = args.recipient
            message["Subject"] = args.subject
            message.set_content(args.body)
            result = smtp.send_message(message)
            emit("send_message", result == {}, rejected=result)

        emit("done", True)
        return 0
    except Exception as exc:
        emit("error", False, error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if smtp is not None:
            try:
                smtp.quit()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
