from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from backend.core.config import PROJECT_ROOT, settings
from backend.core.exceptions import AgentForgeBaseException
from backend.models.constants import ResponseCode


LOCAL_AVATAR_UPLOAD_DIR = PROJECT_ROOT / "uploads" / "avatars"


class AvatarStorageService:
    def upload_avatar(
        self,
        *,
        data: bytes,
        extension: str,
        content_type: str | None,
        request_base_url: str,
    ) -> str:
        provider = settings.AVATAR_STORAGE_PROVIDER.strip().lower()
        if provider == "local":
            return self._upload_local(
                data=data,
                extension=extension,
                request_base_url=request_base_url,
            )
        if provider == "s3":
            return self._upload_s3(
                data=data,
                extension=extension,
                content_type=content_type,
            )
        raise AgentForgeBaseException(
            f"Unsupported avatar storage provider: {settings.AVATAR_STORAGE_PROVIDER}",
            code=ResponseCode.INTERNAL_ERROR,
            status_code=500,
        )

    def _upload_local(self, *, data: bytes, extension: str, request_base_url: str) -> str:
        LOCAL_AVATAR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}{extension}"
        destination = LOCAL_AVATAR_UPLOAD_DIR / filename
        destination.write_bytes(data)

        public_base = settings.AVATAR_PUBLIC_BASE_URL.strip().rstrip("/")
        if public_base:
            return f"{public_base}/{filename}"
        return f"{request_base_url.rstrip('/')}/uploads/avatars/{filename}"

    def _upload_s3(self, *, data: bytes, extension: str, content_type: str | None) -> str:
        bucket = settings.OBJECT_STORAGE_BUCKET.strip()
        endpoint = settings.OBJECT_STORAGE_ENDPOINT.strip()
        public_base = settings.OBJECT_STORAGE_PUBLIC_BASE_URL.strip().rstrip("/")
        if not bucket or not endpoint or not settings.OBJECT_STORAGE_ACCESS_KEY.strip() or not settings.OBJECT_STORAGE_SECRET_KEY.strip():
            raise AgentForgeBaseException(
                "Object storage is not fully configured for avatar uploads",
                code=ResponseCode.INTERNAL_ERROR,
                status_code=500,
            )

        key = f"avatars/{uuid.uuid4().hex}{extension}"
        client = self._create_s3_client()
        extra_args: dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type or "application/octet-stream",
        }
        if settings.OBJECT_STORAGE_PUBLIC_READ:
            extra_args["ACL"] = "public-read"

        try:
            client.put_object(**extra_args)
        except Exception as exc:
            raise AgentForgeBaseException(
                f"Avatar upload to object storage failed: {type(exc).__name__}: {exc}",
                code=ResponseCode.INTERNAL_ERROR,
                status_code=500,
            ) from exc

        if public_base:
            return f"{public_base}/{key}"
        endpoint_base = endpoint.rstrip("/")
        if settings.OBJECT_STORAGE_FORCE_PATH_STYLE:
            return f"{endpoint_base}/{bucket}/{key}"
        return f"{endpoint_base}/{key}"

    def _create_s3_client(self):
        try:
            import boto3
        except ImportError as exc:
            raise AgentForgeBaseException(
                "boto3 is required for S3 avatar uploads",
                code=ResponseCode.INTERNAL_ERROR,
                status_code=500,
            ) from exc

        session = boto3.session.Session()
        return session.client(
            "s3",
            endpoint_url=settings.OBJECT_STORAGE_ENDPOINT,
            region_name=settings.OBJECT_STORAGE_REGION or None,
            aws_access_key_id=settings.OBJECT_STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.OBJECT_STORAGE_SECRET_KEY,
            use_ssl=settings.OBJECT_STORAGE_USE_SSL,
            verify=settings.OBJECT_STORAGE_VERIFY_TLS,
        )


avatar_storage_service = AvatarStorageService()
