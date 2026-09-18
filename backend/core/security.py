import base64
import hashlib
import ipaddress
from typing import Optional
from urllib.parse import urlparse

from backend.core.config import settings
from backend.core.exceptions import AgentForgeBaseException
from backend.models.constants import ResponseCode
from backend.models.constants import ArcErrorCode


def _keystream(secret: str, length: int) -> bytes:
    seed = secret.encode("utf-8")
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(seed + str(counter).encode("utf-8")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_api_key(plain_text: str) -> str:
    data = plain_text.encode("utf-8")
    stream = _keystream(settings.AGENT_CONFIG_SECRET, len(data))
    cipher = bytes(a ^ b for a, b in zip(data, stream))
    return "v1:" + base64.urlsafe_b64encode(cipher).decode("utf-8")


def decrypt_api_key(cipher_text: str) -> str:
    if not cipher_text.startswith("v1:"):
        raise AgentForgeBaseException(
            message="Invalid encrypted key format",
            code=ResponseCode.VALIDATION_ERROR,
            status_code=422,
            data={"error": {"code": ArcErrorCode.AUTH_FAILED.value, "message": "Invalid encrypted key format"}},
        )
    payload = cipher_text[3:]
    raw = base64.urlsafe_b64decode(payload.encode("utf-8"))
    stream = _keystream(settings.AGENT_CONFIG_SECRET, len(raw))
    plain = bytes(a ^ b for a, b in zip(raw, stream))
    return plain.decode("utf-8")


def validate_provider_url(url: str) -> None:
    parsed = urlparse(url.strip())
    host: Optional[str] = parsed.hostname.lower() if parsed.hostname else None
    if parsed.scheme not in {"http", "https"} or host is None:
        raise AgentForgeBaseException(
            message="Invalid endpoint URL",
            code=ResponseCode.VALIDATION_ERROR,
            status_code=422,
            data={"error": {"code": ArcErrorCode.INVALID_ENDPOINT.value, "message": "Invalid endpoint URL"}},
        )

    blocked_hosts = {"localhost", "host.docker.internal", "docker.internal"}
    if host in blocked_hosts or host.endswith(".docker.internal"):
        raise AgentForgeBaseException(
            message="Endpoint host is blocked",
            code=ResponseCode.VALIDATION_ERROR,
            status_code=422,
            data={"error": {"code": ArcErrorCode.INVALID_ENDPOINT.value, "message": "Endpoint host is blocked"}},
        )

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback or ip.is_private or ip.is_link_local:
            raise AgentForgeBaseException(
                message="Endpoint IP is blocked",
                code=ResponseCode.VALIDATION_ERROR,
                status_code=422,
                data={"error": {"code": ArcErrorCode.INVALID_ENDPOINT.value, "message": "Endpoint IP is blocked"}},
            )
    except ValueError:
        # Hostname is not a direct IP; still hard-block obvious local aliases.
        if host.endswith(".local"):
            raise AgentForgeBaseException(
                message="Local endpoint is blocked",
                code=ResponseCode.VALIDATION_ERROR,
                status_code=422,
                data={"error": {"code": ArcErrorCode.INVALID_ENDPOINT.value, "message": "Local endpoint is blocked"}},
            )
