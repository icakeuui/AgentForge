from __future__ import annotations

import argparse
import json
import re
import signal
import socketserver
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


CODE_PATTERN = re.compile(r"\b(\d{6})\b")


@dataclass(slots=True)
class CapturedMessage:
    id: int
    created_at: str
    sender: str
    recipients: list[str]
    subject: str
    body: str
    raw: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "sender": self.sender,
            "recipients": self.recipients,
            "subject": self.subject,
            "body": self.body,
            "raw": self.raw,
        }


class MessageStore:
    def __init__(self, store_file: Path | None = None) -> None:
        self._messages: list[CapturedMessage] = []
        self._lock = threading.RLock()
        self._changed = threading.Condition(self._lock)
        self._store_file = store_file

    def add(self, *, sender: str, recipients: list[str], raw_bytes: bytes) -> CapturedMessage:
        parsed = BytesParser(policy=policy.default).parsebytes(raw_bytes)
        subject = str(parsed.get("Subject") or "")
        body = _extract_body(parsed)
        raw = raw_bytes.decode("utf-8", errors="replace")
        with self._changed:
            message = CapturedMessage(
                id=len(self._messages) + 1,
                created_at=datetime.now(timezone.utc).isoformat(),
                sender=sender,
                recipients=recipients,
                subject=subject,
                body=body,
                raw=raw,
            )
            self._messages.append(message)
            self._persist_locked()
            self._changed.notify_all()
            return message

    def clear(self) -> None:
        with self._changed:
            self._messages.clear()
            self._persist_locked()
            self._changed.notify_all()

    def list(
        self,
        *,
        recipient: str | None = None,
        subject_contains: str | None = None,
        body_contains: str | None = None,
        limit: int | None = None,
    ) -> list[CapturedMessage]:
        recipient_normalized = recipient.strip().lower() if recipient else None
        subject_normalized = subject_contains.lower() if subject_contains else None
        body_normalized = body_contains.lower() if body_contains else None
        with self._lock:
            messages = list(self._messages)
        filtered: list[CapturedMessage] = []
        for message in messages:
            if recipient_normalized and recipient_normalized not in {value.lower() for value in message.recipients}:
                continue
            if subject_normalized and subject_normalized not in message.subject.lower():
                continue
            if body_normalized and body_normalized not in message.body.lower():
                continue
            filtered.append(message)
        if limit is not None:
            return filtered[-limit:]
        return filtered

    def wait_for_message(
        self,
        *,
        recipient: str | None = None,
        subject_contains: str | None = None,
        body_contains: str | None = None,
        timeout: float = 10.0,
    ) -> CapturedMessage:
        deadline = time.monotonic() + timeout
        with self._changed:
            while True:
                matches = self.list(
                    recipient=recipient,
                    subject_contains=subject_contains,
                    body_contains=body_contains,
                )
                if matches:
                    return matches[-1]
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Timed out waiting for SMTP message")
                self._changed.wait(timeout=remaining)

    def wait_for_code(
        self,
        *,
        recipient: str,
        subject_contains: str | None = None,
        timeout: float = 10.0,
    ) -> str:
        message = self.wait_for_message(
            recipient=recipient,
            subject_contains=subject_contains,
            timeout=timeout,
        )
        code = extract_code(message.body)
        if code is None:
            raise ValueError("No verification code found in message body")
        return code

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [message.to_dict() for message in self._messages]

    def _persist_locked(self) -> None:
        if self._store_file is None:
            return
        self._store_file.parent.mkdir(parents=True, exist_ok=True)
        self._store_file.write_text(
            json.dumps({"messages": [message.to_dict() for message in self._messages]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class ThreadedSmtpServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], request_handler: type[socketserver.StreamRequestHandler], store: MessageStore):
        super().__init__(server_address, request_handler)
        self.store = store


class SmtpCaptureHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.wfile.write(b"220 AgentForge SMTP Capture\r\n")
        sender = ""
        recipients: list[str] = []
        data_mode = False
        data_lines: list[bytes] = []

        while True:
            line = self.rfile.readline()
            if not line:
                break

            if data_mode:
                if line in {b".\r\n", b".\n"}:
                    message = self.server.store.add(sender=sender, recipients=recipients, raw_bytes=b"".join(data_lines))
                    print(
                        json.dumps(
                            {
                                "event": "smtp_message_captured",
                                "id": message.id,
                                "to": message.recipients,
                                "subject": message.subject,
                                "code": extract_code(message.body),
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    data_mode = False
                    data_lines = []
                    self.wfile.write(b"250 Message accepted\r\n")
                    continue
                if line.startswith(b".."):
                    line = line[1:]
                data_lines.append(line)
                continue

            command = line.decode("utf-8", errors="replace").strip()
            upper = command.upper()

            if upper.startswith("EHLO") or upper.startswith("HELO"):
                self.wfile.write(b"250-localhost\r\n250 OK\r\n")
            elif upper.startswith("MAIL FROM:"):
                sender = _normalize_address(command[len("MAIL FROM:") :])
                recipients = []
                self.wfile.write(b"250 OK\r\n")
            elif upper.startswith("RCPT TO:"):
                recipients.append(_normalize_address(command[len("RCPT TO:") :]))
                self.wfile.write(b"250 OK\r\n")
            elif upper == "DATA":
                data_mode = True
                data_lines = []
                self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
            elif upper == "RSET":
                sender = ""
                recipients = []
                data_mode = False
                data_lines = []
                self.wfile.write(b"250 OK\r\n")
            elif upper == "NOOP":
                self.wfile.write(b"250 OK\r\n")
            elif upper == "QUIT":
                self.wfile.write(b"221 Bye\r\n")
                break
            else:
                self.wfile.write(b"250 OK\r\n")


class HttpCaptureHandler(BaseHTTPRequestHandler):
    server: "CaptureHttpServer"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write_json(
                {
                    "ok": True,
                    "smtp_port": self.server.capture_service.smtp_port,
                    "http_port": self.server.capture_service.http_port,
                    "messages": len(self.server.capture_service.store.snapshot()),
                }
            )
            return
        if parsed.path == "/messages":
            query = parse_qs(parsed.query)
            limit = _parse_optional_int(query.get("limit", [None])[0])
            messages = self.server.capture_service.store.list(
                recipient=query.get("recipient", [None])[0],
                subject_contains=query.get("subject_contains", [None])[0],
                body_contains=query.get("body_contains", [None])[0],
                limit=limit,
            )
            self._write_json({"messages": [message.to_dict() for message in messages]})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/messages":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self.server.capture_service.store.clear()
        self._write_json({"ok": True})

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class CaptureHttpServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], request_handler: type[BaseHTTPRequestHandler], capture_service: "SmtpCaptureServer") -> None:
        super().__init__(server_address, request_handler)
        self.capture_service = capture_service


class SmtpCaptureServer:
    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        smtp_port: int = 0,
        http_port: int = 0,
        store_file: str | Path | None = None,
    ) -> None:
        self.host = host
        self.store = MessageStore(Path(store_file) if store_file else None)
        self.smtp_port = smtp_port
        self.http_port = http_port
        self._smtp_server: ThreadedSmtpServer | None = None
        self._http_server: CaptureHttpServer | None = None
        self._smtp_thread: threading.Thread | None = None
        self._http_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._smtp_server is not None or self._http_server is not None:
            raise RuntimeError("SMTP capture server already started")

        self._smtp_server = ThreadedSmtpServer((self.host, self.smtp_port), SmtpCaptureHandler, self.store)
        self.smtp_port = int(self._smtp_server.server_address[1])
        self._smtp_thread = threading.Thread(target=self._smtp_server.serve_forever, name="smtp-capture", daemon=True)
        self._smtp_thread.start()

        self._http_server = CaptureHttpServer((self.host, self.http_port), HttpCaptureHandler, self)
        self.http_port = int(self._http_server.server_address[1])
        self._http_thread = threading.Thread(target=self._http_server.serve_forever, name="smtp-capture-http", daemon=True)
        self._http_thread.start()

    def stop(self) -> None:
        if self._http_server is not None:
            self._http_server.shutdown()
            self._http_server.server_close()
        if self._smtp_server is not None:
            self._smtp_server.shutdown()
            self._smtp_server.server_close()
        if self._http_thread is not None:
            self._http_thread.join(timeout=2)
        if self._smtp_thread is not None:
            self._smtp_thread.join(timeout=2)
        self._http_server = None
        self._smtp_server = None
        self._http_thread = None
        self._smtp_thread = None

    def wait_for_message(
        self,
        *,
        recipient: str | None = None,
        subject_contains: str | None = None,
        body_contains: str | None = None,
        timeout: float = 10.0,
    ) -> CapturedMessage:
        return self.store.wait_for_message(
            recipient=recipient,
            subject_contains=subject_contains,
            body_contains=body_contains,
            timeout=timeout,
        )

    def wait_for_code(
        self,
        *,
        recipient: str,
        subject_contains: str | None = None,
        timeout: float = 10.0,
    ) -> str:
        return self.store.wait_for_code(
            recipient=recipient,
            subject_contains=subject_contains,
            timeout=timeout,
        )


def extract_code(body: str) -> str | None:
    match = CODE_PATTERN.search(body)
    if match is None:
        return None
    return match.group(1)


def _extract_body(message: Any) -> str:
    if hasattr(message, "is_multipart") and message.is_multipart():
        parts: list[str] = []
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_type() != "text/plain":
                continue
            content = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            parts.append((content or b"").decode(charset, errors="replace"))
        return "\n".join(part for part in parts if part)

    try:
        return str(message.get_content())
    except Exception:
        payload = message.get_payload(decode=True)
        if isinstance(payload, bytes):
            return payload.decode(message.get_content_charset() or "utf-8", errors="replace")
        if isinstance(payload, str):
            return payload
        return ""


def _normalize_address(value: str) -> str:
    _, address = parseaddr(value.strip())
    if address:
        return address.lower()
    return value.strip().strip("<>").lower()


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local SMTP capture server for AgentForge e2e")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--smtp-port", type=int, default=3025)
    parser.add_argument("--http-port", type=int, default=8025)
    parser.add_argument("--store-file", default=None)
    args = parser.parse_args()

    server = SmtpCaptureServer(
        host=args.host,
        smtp_port=args.smtp_port,
        http_port=args.http_port,
        store_file=args.store_file,
    )
    stop_event = threading.Event()

    def _stop(*_: Any) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    server.start()
    print(
        json.dumps(
            {
                "ok": True,
                "host": server.host,
                "smtp_port": server.smtp_port,
                "http_port": server.http_port,
                "store_file": args.store_file,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    try:
        while not stop_event.wait(1):
            pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
