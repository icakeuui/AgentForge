from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.exceptions import ValidationException
from backend.models.schemas import (
    AuthContext,
    AuthUserProfile,
    AvatarUploadResponse,
    BaseResponse,
    LoginRequest,
    PasswordForgotRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterCompleteRequest,
    RegisterStartRequest,
    RegisterStartResponse,
    RegisterVerifyRequest,
    RegisterVerifyResponse,
    TokenPairResponse,
)
from backend.services.account_service import account_service
from backend.services.avatar_storage_service import avatar_storage_service

router = APIRouter(prefix="/auth", tags=["Auth"])
MAX_AVATAR_UPLOAD_BYTES = 5 * 1024 * 1024
AVATAR_CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _avatar_extension(file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    if content_type in AVATAR_CONTENT_TYPE_TO_EXT:
        return AVATAR_CONTENT_TYPE_TO_EXT[content_type]
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    raise ValidationException("请上传 JPG、PNG、WebP 或 GIF 图片")

@router.post("/register/start", response_model=BaseResponse[RegisterStartResponse])
async def register_start(payload: RegisterStartRequest, db: AsyncSession = Depends(get_db)):
    expires_in, retry_after, dev_code = await account_service.start_registration(
        db,
        email=payload.email,
        delivery_mode=payload.delivery_mode,
    )
    return BaseResponse.success(
        data=RegisterStartResponse(
            email=payload.email,
            expires_in_seconds=expires_in,
            retry_after_seconds=retry_after,
            dev_code=dev_code,
        ),
        message="Verification email sent",
    )


@router.post("/register/verify", response_model=BaseResponse[RegisterVerifyResponse])
async def register_verify(payload: RegisterVerifyRequest, db: AsyncSession = Depends(get_db)):
    registration_token = await account_service.verify_registration(
        db,
        email=payload.email,
        code=payload.code,
    )
    return BaseResponse.success(
        data=RegisterVerifyResponse(
            email=payload.email,
            registration_token=registration_token,
            expires_in_seconds=settings.REGISTRATION_TOKEN_TTL_SECONDS,
        ),
        message="Email verified",
    )


@router.post("/register/complete", response_model=BaseResponse[TokenPairResponse])
async def register_complete(payload: RegisterCompleteRequest, db: AsyncSession = Depends(get_db)):
    token_pair = await account_service.complete_registration(
        db,
        email=payload.email,
        registration_token=payload.registration_token,
        password=payload.password,
        confirm_password=payload.confirm_password,
        display_name=payload.display_name,
        avatar_url=payload.avatar_url,
    )
    return BaseResponse.success(data=token_pair, message="Registered successfully")


@router.post("/avatar/upload", response_model=BaseResponse[AvatarUploadResponse])
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    extension = _avatar_extension(file)
    raw_data = await file.read()
    if not raw_data:
        raise ValidationException("头像文件不能为空")
    if len(raw_data) > MAX_AVATAR_UPLOAD_BYTES:
        raise ValidationException("头像文件不能超过 5MB")

    avatar_url = avatar_storage_service.upload_avatar(
        data=raw_data,
        extension=extension,
        content_type=file.content_type,
        request_base_url=str(request.base_url),
    )
    return BaseResponse.success(
        data=AvatarUploadResponse(avatar_url=avatar_url),
        message="Avatar uploaded",
    )


@router.post("/login", response_model=BaseResponse[TokenPairResponse])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    token_pair = await account_service.login(db, email=payload.email, password=payload.password)
    return BaseResponse.success(data=token_pair, message="Logged in")


@router.post("/refresh", response_model=BaseResponse[TokenPairResponse])
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    token_pair = await account_service.refresh(db, refresh_token=payload.refresh_token)
    return BaseResponse.success(data=token_pair, message="Refreshed")


@router.post("/logout", response_model=BaseResponse[None])
async def logout(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    await account_service.logout(db, refresh_token=payload.refresh_token)
    return BaseResponse.success(message="Logged out")


@router.post("/password/forgot", response_model=BaseResponse[RegisterStartResponse])
async def password_forgot(payload: PasswordForgotRequest, db: AsyncSession = Depends(get_db)):
    expires_in, dev_code = await account_service.start_password_reset(db, email=payload.email)
    return BaseResponse.success(
        data=RegisterStartResponse(
            email=payload.email,
            expires_in_seconds=expires_in,
            retry_after_seconds=settings.EMAIL_SEND_RATE_LIMIT_SECONDS,
            dev_code=dev_code,
        ),
        message="If the email exists, a reset code has been sent",
    )


@router.post("/password/reset", response_model=BaseResponse[None])
async def password_reset(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    await account_service.reset_password(
        db,
        email=payload.email,
        code=payload.code,
        new_password=payload.new_password,
    )
    return BaseResponse.success(message="Password reset")


@router.get("/session", response_model=BaseResponse[AuthUserProfile])
async def session(auth: AuthContext = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile = await account_service.get_profile_for_auth(db, auth)
    return BaseResponse.success(data=profile, message="OK")
