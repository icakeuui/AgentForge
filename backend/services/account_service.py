from __future__ import annotations

import hashlib
import inspect
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.exceptions import AuthException, FlowException, NotFoundException
from backend.models.constants import ResponseCode
from backend.models.orm import (
    EmailVerificationCode,
    RefreshToken,
    Team,
    TeamMember,
    TeamQuota,
    User,
    UserCredential,
)
from backend.models.schemas import AuthContext, AuthUserProfile, PublicUserProfile, TokenPairResponse
from backend.services.email_service import EmailDeliveryError, email_service
from backend.services.password_service import password_service
from backend.services.search_id_service import search_id_service
from backend.services.token_service import token_service


REGISTER_PURPOSE = "register"
RESET_PASSWORD_PURPOSE = "reset_password"
MAX_CODE_ATTEMPTS = 5

FLOW_ERROR_CODES = {
    "EMAIL_ALREADY_REGISTERED": ResponseCode.EMAIL_ALREADY_REGISTERED,
    "EMAIL_SEND_RATE_LIMITED": ResponseCode.EMAIL_SEND_RATE_LIMITED,
    "EMAIL_PROVIDER_NOT_CONFIGURED": ResponseCode.EMAIL_PROVIDER_NOT_CONFIGURED,
    "EMAIL_SEND_FAILED": ResponseCode.EMAIL_SEND_FAILED,
    "VERIFICATION_CODE_INVALID": ResponseCode.VERIFICATION_CODE_INVALID,
    "VERIFICATION_CODE_EXPIRED": ResponseCode.VERIFICATION_CODE_EXPIRED,
    "VERIFICATION_CODE_ATTEMPTS_EXCEEDED": ResponseCode.VERIFICATION_CODE_ATTEMPTS_EXCEEDED,
    "REGISTRATION_TOKEN_INVALID": ResponseCode.REGISTRATION_TOKEN_INVALID,
    "REGISTRATION_TOKEN_EXPIRED": ResponseCode.REGISTRATION_TOKEN_EXPIRED,
    "PASSWORD_CONFIRM_MISMATCH": ResponseCode.PASSWORD_CONFIRM_MISMATCH,
    "ACCOUNT_DISABLED": ResponseCode.ACCOUNT_DISABLED,
}


class AccountService:
    async def start_registration(
        self,
        session: AsyncSession,
        *,
        email: str,
        delivery_mode: str | None = None,
    ) -> tuple[int, int, str | None]:
        email = self._normalize_email(email)
        await self._ensure_email_available(session, email)
        await self._ensure_send_not_rate_limited(session, email=email, purpose=REGISTER_PURPOSE)
        await self._invalidate_unconsumed_codes(session, email=email, purpose=REGISTER_PURPOSE)
        code = self._new_code()
        verification = EmailVerificationCode(
            id=uuid.uuid4(),
            email=email,
            purpose=REGISTER_PURPOSE,
            code_hash=self._hash_code(email=email, purpose=REGISTER_PURPOSE, code=code),
            send_status="PENDING",
            send_attempts=0,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.EMAIL_VERIFICATION_CODE_TTL_SECONDS),
        )
        session.add(verification)
        await session.flush()
        try:
            send_result = email_service.send_verification_code(
                to_email=email,
                code=code,
                purpose=REGISTER_PURPOSE,
                delivery_mode=delivery_mode,
            )
            if inspect.isawaitable(send_result):
                send_result = await send_result
        except EmailDeliveryError as exc:
            verification.send_status = "FAILED"
            verification.send_attempts = exc.attempts or 1
            verification.last_send_error = exc.message[:500]
            await session.commit()
            raise self._flow_error(
                exc.error_code,
                exc.message,
                data={
                    "provider": exc.provider,
                    "attempts": exc.attempts or 1,
                    "smtp_stage": exc.stage,
                    "error_detail": exc.detail,
                },
            ) from exc

        verification.send_status = "SENT"
        verification.send_attempts = getattr(send_result, "attempts", 1) or 1
        verification.sent_at = datetime.now(timezone.utc)
        verification.last_send_error = None
        await session.commit()
        dev_code = send_result if isinstance(send_result, str) else getattr(send_result, "dev_code", None)
        return (
            settings.EMAIL_VERIFICATION_CODE_TTL_SECONDS,
            settings.EMAIL_SEND_RATE_LIMIT_SECONDS,
            dev_code,
        )

    async def verify_registration(self, session: AsyncSession, *, email: str, code: str) -> str:
        email = self._normalize_email(email)
        verification = await self._get_latest_verification_code(session, email=email, purpose=REGISTER_PURPOSE)
        if verification is None:
            raise self._flow_error("VERIFICATION_CODE_INVALID", "Verification code is invalid")
        now = datetime.now(timezone.utc)
        if self._as_utc(verification.expires_at) <= now:
            raise self._flow_error("VERIFICATION_CODE_EXPIRED", "Verification code is expired")
        expected_hash = self._hash_code(email=email, purpose=REGISTER_PURPOSE, code=code)
        if not secrets.compare_digest(verification.code_hash, expected_hash):
            verification.verification_attempts += 1
            await session.commit()
            if verification.verification_attempts > MAX_CODE_ATTEMPTS:
                raise self._flow_error("VERIFICATION_CODE_ATTEMPTS_EXCEEDED", "Verification code attempts exceeded")
            raise self._flow_error("VERIFICATION_CODE_INVALID", "Verification code is invalid")
        verification.consumed_at = now
        await session.commit()
        return self._create_registration_token(email)

    async def complete_registration(
        self,
        session: AsyncSession,
        *,
        email: str,
        registration_token: str,
        password: str,
        confirm_password: str,
        display_name: str,
        avatar_url: str | None,
    ) -> TokenPairResponse:
        email = self._normalize_email(email)
        if password != confirm_password:
            raise self._flow_error("PASSWORD_CONFIRM_MISMATCH", "Passwords do not match")
        self._verify_registration_token(email=email, registration_token=registration_token)
        await self._ensure_email_available(session, email)

        user_id = f"user_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)
        try:
            search_id = await search_id_service.allocate(session, user_id=user_id)
            team = Team(id=uuid.uuid4(), name=f"{display_name}'s Team", status="ACTIVE")
            team_member = TeamMember(team_id=team.id, user_id=user_id, role="owner", status="ACTIVE")
            user = User(
                user_id=user_id,
                search_id=search_id,
                email=email,
                email_verified=True,
                display_name=display_name,
                avatar_url=avatar_url or None,
                status="ACTIVE",
            )
            credential = UserCredential(
                user_id=user_id,
                password_hash=password_service.hash_password(password),
                password_updated_at=now,
            )
            quota = TeamQuota(
                team_id=team.id,
                token_limit=settings.DEFAULT_TEAM_TOKEN_LIMIT,
                rate_limit=settings.DEFAULT_TEAM_RATE_LIMIT,
            )
            session.add_all([user, credential, team, team_member, quota])
            await session.flush()
            response = await token_service.issue_token_pair(session, user=user, team_member=team_member)
            await session.commit()
            return response
        except IntegrityError as exc:
            await session.rollback()
            raise self._flow_error("EMAIL_ALREADY_REGISTERED", "Email is already registered") from exc

    async def login(self, session: AsyncSession, *, email: str, password: str) -> TokenPairResponse:
        email = self._normalize_email(email)
        user = await self._get_user_by_email(session, email)
        if user is None:
            raise AuthException("Invalid email or password", code=ResponseCode.TOKEN_INVALID)
        if user.status != "ACTIVE":
            raise self._flow_error("ACCOUNT_DISABLED", "Account is disabled", status_code=403)
        if not user.email_verified:
            raise AuthException("Invalid email or password", code=ResponseCode.TOKEN_INVALID)
        credential = await session.get(UserCredential, user.user_id)
        if credential is None or not password_service.verify_password(password, credential.password_hash):
            raise AuthException("Invalid email or password", code=ResponseCode.TOKEN_INVALID)
        team_member = await self._get_active_team_member(session, user.user_id)
        if team_member is None:
            raise AuthException("No active team for user", code=ResponseCode.TOKEN_INVALID)
        response = await token_service.issue_token_pair(session, user=user, team_member=team_member)
        await session.commit()
        return response

    async def refresh(self, session: AsyncSession, *, refresh_token: str) -> TokenPairResponse:
        token_record = await token_service.get_active_refresh_token(session, refresh_token)
        if token_record is None:
            raise AuthException("Invalid refresh token", code=ResponseCode.TOKEN_INVALID)
        user = await session.get(User, token_record.user_id)
        if user is None or user.status != "ACTIVE":
            raise AuthException("Invalid refresh token", code=ResponseCode.TOKEN_INVALID)
        team_member = await self._get_active_team_member(session, user.user_id)
        if team_member is None:
            raise AuthException("No active team for user", code=ResponseCode.TOKEN_INVALID)
        token_record.revoked_at = datetime.now(timezone.utc)
        response = await token_service.issue_token_pair(session, user=user, team_member=team_member)
        await session.commit()
        return response

    async def logout(self, session: AsyncSession, *, refresh_token: str | None) -> None:
        if refresh_token:
            await token_service.revoke_refresh_token(session, refresh_token)
            await session.commit()

    async def start_password_reset(self, session: AsyncSession, *, email: str) -> tuple[int, str | None]:
        email = self._normalize_email(email)
        user = await self._get_user_by_email(session, email)
        if user is None or user.status != "ACTIVE":
            return settings.PASSWORD_RESET_CODE_TTL_SECONDS, None
        await self._ensure_send_not_rate_limited(session, email=email, purpose=RESET_PASSWORD_PURPOSE)
        await self._invalidate_unconsumed_codes(session, email=email, purpose=RESET_PASSWORD_PURPOSE)
        code = self._new_code()
        verification = EmailVerificationCode(
            id=uuid.uuid4(),
            email=email,
            purpose=RESET_PASSWORD_PURPOSE,
            code_hash=self._hash_code(email=email, purpose=RESET_PASSWORD_PURPOSE, code=code),
            send_status="PENDING",
            send_attempts=0,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.PASSWORD_RESET_CODE_TTL_SECONDS),
        )
        session.add(verification)
        await session.flush()
        try:
            send_result = email_service.send_verification_code(
                to_email=email,
                code=code,
                purpose=RESET_PASSWORD_PURPOSE,
            )
            if inspect.isawaitable(send_result):
                send_result = await send_result
        except EmailDeliveryError as exc:
            verification.send_status = "FAILED"
            verification.send_attempts = exc.attempts or 1
            verification.last_send_error = exc.message[:500]
            await session.commit()
            raise self._flow_error(
                exc.error_code,
                exc.message,
                data={
                    "provider": exc.provider,
                    "attempts": exc.attempts or 1,
                    "smtp_stage": exc.stage,
                    "error_detail": exc.detail,
                },
            ) from exc

        verification.send_status = "SENT"
        verification.send_attempts = getattr(send_result, "attempts", 1) or 1
        verification.sent_at = datetime.now(timezone.utc)
        verification.last_send_error = None
        await session.commit()
        dev_code = send_result if isinstance(send_result, str) else getattr(send_result, "dev_code", None)
        return settings.PASSWORD_RESET_CODE_TTL_SECONDS, dev_code

    async def reset_password(self, session: AsyncSession, *, email: str, code: str, new_password: str) -> None:
        email = self._normalize_email(email)
        user = await self._get_user_by_email(session, email)
        if user is None or user.status != "ACTIVE":
            raise AuthException("Invalid reset code", code=ResponseCode.TOKEN_INVALID)
        verification = await self._consume_code(session, email=email, purpose=RESET_PASSWORD_PURPOSE, code=code)
        credential = await session.get(UserCredential, user.user_id)
        now = datetime.now(timezone.utc)
        if credential is None:
            credential = UserCredential(user_id=user.user_id, password_hash="", password_updated_at=now)
            session.add(credential)
        credential.password_hash = password_service.hash_password(new_password)
        credential.password_updated_at = now
        verification.consumed_at = now
        await session.commit()

    async def get_profile_for_auth(self, session: AsyncSession, auth: AuthContext) -> AuthUserProfile:
        user = await session.get(User, auth.user_id)
        if user is None:
            if auth.is_dev and auth.auth_mode == "dev_bypass":
                return AuthUserProfile(
                    user_id=auth.user_id,
                    search_id=auth.search_id or 0,
                    email=auth.email or "dev@example.local",
                    email_verified=True,
                    display_name="Dev User",
                    status="ACTIVE",
                    team_id=auth.team_id,
                    role=auth.role,
                )
            raise NotFoundException("User not found")
        team_member = await self._get_active_team_member(session, user.user_id)
        team_id = auth.team_id
        role = auth.role
        if team_member is not None:
            team_id = str(team_member.team_id)
            role = team_member.role
        return self._profile(user, team_id=team_id, role=role)

    async def get_public_profile_by_search_id(self, session: AsyncSession, search_id: int) -> PublicUserProfile:
        result = await session.execute(select(User).where(User.search_id == search_id, User.status == "ACTIVE"))
        user = result.scalar_one_or_none()
        if user is None:
            raise NotFoundException("User not found")
        return self._public_profile(user)

    async def get_profile_by_user_id(self, session: AsyncSession, user_id: str) -> AuthUserProfile:
        user = await session.get(User, user_id)
        if user is None or user.status != "ACTIVE":
            raise NotFoundException("User not found")
        team_member = await self._get_active_team_member(session, user.user_id)
        return self._profile(user, team_id=str(team_member.team_id) if team_member else None, role=team_member.role if team_member else None)

    async def _get_user_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def _get_active_team_member(self, session: AsyncSession, user_id: str) -> TeamMember | None:
        result = await session.execute(
            select(TeamMember)
            .where(TeamMember.user_id == user_id, TeamMember.status == "ACTIVE")
            .order_by(TeamMember.created_at.asc())
        )
        return result.scalars().first()

    async def _ensure_email_available(self, session: AsyncSession, email: str) -> None:
        user = await self._get_user_by_email(session, email)
        if user is not None:
            raise self._flow_error("EMAIL_ALREADY_REGISTERED", "Email is already registered", status_code=409)

    async def _ensure_send_not_rate_limited(self, session: AsyncSession, *, email: str, purpose: str) -> None:
        latest = await self._get_latest_verification_code(session, email=email, purpose=purpose)
        if latest is None:
            return
        now = datetime.now(timezone.utc)
        latest_base = latest.sent_at or latest.created_at
        latest_base = self._as_utc(latest_base)
        retry_after = settings.EMAIL_SEND_RATE_LIMIT_SECONDS - int((now - latest_base).total_seconds())
        if retry_after > 0 and latest.invalidated_at is None and latest.consumed_at is None:
            raise self._flow_error(
                "EMAIL_SEND_RATE_LIMITED",
                "Verification email was sent too recently",
                data={"retry_after_seconds": retry_after},
                status_code=429,
            )

    async def _invalidate_unconsumed_codes(self, session: AsyncSession, *, email: str, purpose: str) -> None:
        result = await session.execute(
            select(EmailVerificationCode).where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.consumed_at.is_(None),
                EmailVerificationCode.invalidated_at.is_(None),
            )
        )
        now = datetime.now(timezone.utc)
        for code in result.scalars().all():
            code.invalidated_at = now

    async def _get_latest_code_any_status(
        self,
        session: AsyncSession,
        *,
        email: str,
        purpose: str,
    ) -> EmailVerificationCode | None:
        result = await session.execute(
            select(EmailVerificationCode)
            .where(EmailVerificationCode.email == email, EmailVerificationCode.purpose == purpose)
            .order_by(desc(EmailVerificationCode.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_latest_verification_code(
        self,
        session: AsyncSession,
        *,
        email: str,
        purpose: str,
    ) -> EmailVerificationCode | None:
        result = await session.execute(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.purpose == purpose,
                EmailVerificationCode.send_status == "SENT",
                EmailVerificationCode.consumed_at.is_(None),
                EmailVerificationCode.invalidated_at.is_(None),
            )
            .order_by(desc(EmailVerificationCode.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _consume_code(
        self,
        session: AsyncSession,
        *,
        email: str,
        purpose: str,
        code: str,
    ) -> EmailVerificationCode:
        verification = await self._get_latest_verification_code(session, email=email, purpose=purpose)
        if verification is None:
            raise self._flow_error("VERIFICATION_CODE_INVALID", "Verification code is invalid")
        now = datetime.now(timezone.utc)
        if self._as_utc(verification.expires_at) <= now:
            raise self._flow_error("VERIFICATION_CODE_EXPIRED", "Verification code is expired")
        expected_hash = self._hash_code(email=email, purpose=purpose, code=code)
        if not secrets.compare_digest(verification.code_hash, expected_hash):
            verification.verification_attempts += 1
            await session.commit()
            if verification.verification_attempts > MAX_CODE_ATTEMPTS:
                raise self._flow_error("VERIFICATION_CODE_ATTEMPTS_EXCEEDED", "Verification code attempts exceeded")
            raise self._flow_error("VERIFICATION_CODE_INVALID", "Verification code is invalid")
        verification.consumed_at = now
        return verification

    def _create_registration_token(self, email: str) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.REGISTRATION_TOKEN_TTL_SECONDS)
        payload = {
            "purpose": REGISTER_PURPOSE,
            "email": email,
            "exp": int(expires_at.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    def _verify_registration_token(self, *, email: str, registration_token: str) -> None:
        try:
            payload = jwt.decode(registration_token, settings.JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError as exc:
            raise self._flow_error("REGISTRATION_TOKEN_EXPIRED", "Registration token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise self._flow_error("REGISTRATION_TOKEN_INVALID", "Registration token invalid") from exc
        if payload.get("purpose") != REGISTER_PURPOSE or payload.get("email") != email:
            raise self._flow_error("REGISTRATION_TOKEN_INVALID", "Registration token invalid")

    def _hash_code(self, *, email: str, purpose: str, code: str) -> str:
        raw = f"{settings.JWT_SECRET}:{purpose}:{email}:{code}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _new_code(self) -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    def _normalize_email(self, email: str) -> str:
        normalized = email.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise self._flow_error("VERIFICATION_CODE_INVALID", "Invalid email address", status_code=422)
        return normalized

    def _as_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _profile(self, user: User, *, team_id: str | None = None, role: str | None = None) -> AuthUserProfile:
        return AuthUserProfile(
            user_id=user.user_id,
            search_id=user.search_id,
            email=user.email,
            email_verified=bool(user.email_verified),
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            status=user.status,
            team_id=team_id,
            role=role,
        )

    def _public_profile(self, user: User) -> PublicUserProfile:
        return PublicUserProfile(
            search_id=user.search_id,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            status=user.status,
        )

    def _flow_error(
        self,
        error_code: str,
        message: str,
        *,
        data: dict | None = None,
        status_code: int = 400,
    ) -> FlowException:
        return FlowException(
            message,
            code=FLOW_ERROR_CODES[error_code],
            data={"error_code": error_code, **(data or {})},
            status_code=status_code,
        )


account_service = AccountService()
