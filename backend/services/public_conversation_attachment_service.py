"""Short-lived, isolated text attachments for public agent conversations.

The storage interface keeps routes independent of the local disk implementation.
Only extracted text is persisted; the uploaded binary is discarded after parsing.
"""

import hashlib
import json
import secrets
import shutil
import time
import uuid
from pathlib import Path
from typing import Protocol

from backend.core.config import PROJECT_ROOT
from backend.core.exceptions import ValidationException
from backend.services.knowledge_service import knowledge_service


class AttachmentStorage(Protocol):
    def write(self, key: str, content: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> None: ...
    def list_prefixes(self) -> list[str]: ...


class LocalAttachmentStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, key: str, content: bytes) -> None:
        destination = self.root / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        temporary.write_bytes(content)
        temporary.replace(destination)

    def read(self, key: str) -> bytes:
        return (self.root / key).read_bytes()

    def delete_prefix(self, prefix: str) -> None:
        shutil.rmtree(self.root / prefix, ignore_errors=True)

    def list_prefixes(self) -> list[str]:
        return [entry.name for entry in self.root.iterdir() if entry.is_dir()]


class PublicConversationAttachmentService:
    TTL_SECONDS = 24 * 60 * 60
    MAX_FILES_PER_MESSAGE = 3
    MAX_FILES_PER_CONVERSATION = 20
    MAX_SESSION_BYTES = 200 * 1024 * 1024
    MAX_EXTRACTED_BYTES = 2 * 1024 * 1024
    MAX_CONTEXT_CHARS = 30000

    def __init__(self, storage: AttachmentStorage) -> None:
        self.storage = storage
        self._last_cleanup = 0.0

    def cleanup_expired(self) -> None:
        now = time.time()
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now
        for conversation_id in self.storage.list_prefixes():
            try:
                metadata = json.loads(self.storage.read(f"{conversation_id}/meta.json"))
                if float(metadata["expires_at"]) < now:
                    self.storage.delete_prefix(conversation_id)
            except (OSError, ValueError, KeyError, TypeError):
                # An incomplete upload must not prevent the next conversation.
                continue

    def create(self, *, agent_id: str, slug: str) -> dict[str, str]:
        self.cleanup_expired()
        conversation_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        metadata = {
            "agent_id": agent_id,
            "slug": slug,
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "expires_at": time.time() + self.TTL_SECONDS,
            "files": {},
            "total_bytes": 0,
        }
        self.storage.write(f"{conversation_id}/meta.json", json.dumps(metadata).encode())
        return {"conversation_id": conversation_id, "conversation_token": token}

    def _load(self, *, conversation_id: uuid.UUID, token: str, agent_id: str, slug: str) -> dict:
        try:
            metadata = json.loads(self.storage.read(f"{conversation_id}/meta.json"))
        except (OSError, ValueError) as exc:
            raise ValidationException("公开会话不存在或已过期，请刷新页面重试") from exc
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if (
            not token
            or not secrets.compare_digest(token_hash, metadata.get("token_hash", ""))
            or metadata.get("agent_id") != agent_id
            or metadata.get("slug") != slug
        ):
            raise ValidationException("无权访问此公开会话附件")
        if float(metadata.get("expires_at", 0)) < time.time():
            self.storage.delete_prefix(str(conversation_id))
            raise ValidationException("公开会话已过期，请刷新页面重试")
        return metadata

    def add_file(
        self, *, conversation_id: uuid.UUID, token: str, agent_id: str, slug: str,
        filename: str, content_type: str | None, data: bytes,
    ) -> dict[str, str]:
        metadata = self._load(conversation_id=conversation_id, token=token, agent_id=agent_id, slug=slug)
        if len(metadata["files"]) >= self.MAX_FILES_PER_CONVERSATION:
            raise ValidationException("当前会话附件数量已达上限")
        if metadata["total_bytes"] + len(data) > self.MAX_SESSION_BYTES:
            raise ValidationException("当前会话附件总大小已达上限")
        try:
            title, content = knowledge_service.extract_uploaded_content(
                filename=filename, content_type=content_type, data=data,
            )
        except (ValueError, RuntimeError) as exc:
            raise ValidationException(str(exc)) from exc
        encoded = content.encode("utf-8")
        if len(encoded) > self.MAX_EXTRACTED_BYTES:
            raise ValidationException("文件提取的文本过长，请选择更小的文件")
        file_id = str(uuid.uuid4())
        self.storage.write(f"{conversation_id}/{file_id}.txt", encoded)
        metadata["files"][file_id] = {"name": title, "size": len(data)}
        metadata["total_bytes"] += len(data)
        self.storage.write(f"{conversation_id}/meta.json", json.dumps(metadata, ensure_ascii=False).encode())
        return {"id": file_id, "name": title}

    def context_for_message(
        self, *, conversation_id: uuid.UUID, token: str, agent_id: str, slug: str,
        file_ids: list[uuid.UUID],
    ) -> str:
        metadata = self._load(conversation_id=conversation_id, token=token, agent_id=agent_id, slug=slug)
        if len(file_ids) > self.MAX_FILES_PER_MESSAGE or len(set(file_ids)) != len(file_ids):
            raise ValidationException("单条消息最多可附加 3 个不同文件")
        sections: list[str] = []
        per_file_limit = self.MAX_CONTEXT_CHARS // max(1, len(file_ids))
        for file_id in file_ids:
            entry = metadata["files"].get(str(file_id))
            if entry is None:
                raise ValidationException("附件不属于当前会话")
            content = self.storage.read(f"{conversation_id}/{file_id}.txt").decode("utf-8")
            snippet = content[:per_file_limit]
            limitation = "\n[附件内容过长，仅提供前段文本]" if len(content) > len(snippet) else ""
            sections.append(f"[会话临时附件：{entry['name']}]\n{snippet}{limitation}")
        return "\n\n".join(sections)


public_conversation_attachment_service = PublicConversationAttachmentService(
    # /uploads is publicly mounted by FastAPI; session attachments must stay outside it.
    LocalAttachmentStorage(PROJECT_ROOT / ".tmp" / "public_conversations")
)
