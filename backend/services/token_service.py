from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.orm import RefreshToken, TeamMember, User
from backend.models.schemas import AuthUserProfile, TokenPairResponse


class TokenService:
    def _hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_access_token(self, *, user: User, team_member: TeamMember) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.ACCESS_TOKEN_TTL_SECONDS)
        payload = {
            "ver": 2,
            "sub": user.user_id,
            "user_id": user.user_id,
            "search_id": str(user.search_id),
            "email": user.email,
            "email_verified": bool(user.email_verified),
            "team_id": str(team_member.team_id),
            "role": team_member.role,
            "exp": int(expires_at.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    async def issue_token_pair(self, session: AsyncSession, *, user: User, team_member: TeamMember) -> TokenPairResponse:
        refresh_token = secrets.token_urlsafe(48)
        refresh_record = RefreshToken(
            user_id=user.user_id,
            token_hash=self._hash_refresh_token(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SECONDS),
        )
        session.add(refresh_record)
        await session.flush()
        return TokenPairResponse(
            access_token=self.create_access_token(user=user, team_member=team_member),
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_TTL_SECONDS,
            user=AuthUserProfile(
                user_id=user.user_id,
                search_id=user.search_id,
                email=user.email,
                email_verified=bool(user.email_verified),
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                status=user.status,
                team_id=str(team_member.team_id),
                role=team_member.role,
            ),
        )

    async def get_active_refresh_token(self, session: AsyncSession, refresh_token: str) -> RefreshToken | None:
        token_hash = self._hash_refresh_token(refresh_token)
        result = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        token_record = result.scalar_one_or_none()
        if token_record is None:
            return None
        now = datetime.now(timezone.utc)
        if token_record.revoked_at is not None or self._as_utc(token_record.expires_at) <= now:
            return None
        return token_record

    async def revoke_refresh_token(self, session: AsyncSession, refresh_token: str) -> None:
        token_record = await self.get_active_refresh_token(session, refresh_token)
        if token_record is None:
            return
        token_record.revoked_at = datetime.now(timezone.utc)
        await session.flush()

    def _as_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


token_service = TokenService()
