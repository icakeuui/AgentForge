from typing import Optional
import uuid
from sqlalchemy import select
from backend.models.orm import TeamQuota, Team
from backend.core.rate_limiter import rate_limiter, LimitStatus
from backend.core.config import settings
from backend.core.logging import logger
from backend.models.constants import QuotaStatus
from backend.models.schemas import TeamQuotaStatusData
from backend.core.database import AsyncSessionLocal


class CompetitionManagerService:
    """
    Competition Manager Service - Configuration & Control Layer for Phase 7.
    
    CRITICAL CONSTRAINTS:
    1. Redis Usage: token_usage is ONLY stored in Redis. DB does NOT store token_used.
       No Redis -> DB synchronization is allowed in this phase.
    2. Quota Source: All quota limits (token_limit, rate_limit) must come from DB.
    3. No Cache: Every check queries DB for latest quota config. 
       "Quota Config Cache" is a Phase 10+ optimization and is STRICTLY FORBIDDEN now.
    """
    @staticmethod
    def _is_dev_bypass_team(team_id: str) -> bool:
        return (
            settings.is_dev_env
            and settings.auth_dev_bypass_enabled
            and team_id == settings.AUTH_DEV_TEAM_ID
        )

    async def get_team_quota(self, team_id: str) -> Optional[TeamQuota]:
        try:
            team_uuid = uuid.UUID(team_id)
        except ValueError:
            return None
            
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(TeamQuota).where(TeamQuota.team_id == team_uuid))
            return result.scalar_one_or_none()

    async def get_team(self, team_id: str) -> Optional[Team]:
        try:
            team_uuid = uuid.UUID(team_id)
        except ValueError:
            return None

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Team).where(Team.id == team_uuid))
            return result.scalar_one_or_none()

    async def check_team_rate_limit(self, team_id: str) -> LimitStatus:
        if self._is_dev_bypass_team(team_id):
            logger.bind(
                resource_type="runtime_quota_context",
                resource_id=team_id,
            ).info("dev bypass quota guard: skip rate limit validation")
            return LimitStatus.ALLOWED

        quota = await self.get_team_quota(team_id)
        if not quota:
            return LimitStatus.INFRA_ERROR
        return await rate_limiter.check_rate_limit(team_id, quota.rate_limit)

    async def check_team_token_limit(self, team_id: str) -> LimitStatus:
        if self._is_dev_bypass_team(team_id):
            logger.bind(
                resource_type="runtime_quota_context",
                resource_id=team_id,
            ).info("dev bypass quota guard: skip token limit validation")
            return LimitStatus.ALLOWED

        quota = await self.get_team_quota(team_id)
        if not quota:
            return LimitStatus.INFRA_ERROR
        return await rate_limiter.check_token_limit(team_id, quota.token_limit)

    async def consume_team_quota(self, team_id: str, usage: int) -> None:
        if usage > 0:
            await rate_limiter.add_token_usage(team_id, usage)

    async def get_team_quota_status(self, team_id: str) -> TeamQuotaStatusData:
        quota = await self.get_team_quota(team_id)
        if not quota:
            return TeamQuotaStatusData(
                team_id=team_id,
                token_limit=0,
                token_used=0,
                rate_limit=0,
                current_usage_state="NOT_FOUND",
                quota_status=QuotaStatus.EXHAUSTED,
            )
            
        token_used = await rate_limiter.get_token_usage(team_id)
        if token_used is None:
            token_used = 0
        current_rate_usage = await rate_limiter.get_current_rate_usage(team_id)
        if current_rate_usage is None:
            current_rate_usage = 0
            
        quota_status = QuotaStatus.ACTIVE
        current_usage_state = "NORMAL"
        if token_used >= quota.token_limit:
            quota_status = QuotaStatus.EXHAUSTED
            current_usage_state = "TOKEN_EXHAUSTED"
        elif current_rate_usage >= quota.rate_limit:
            quota_status = QuotaStatus.RATE_LIMITED
            current_usage_state = "RATE_LIMIT_REACHED"
            
        return TeamQuotaStatusData(
            team_id=team_id,
            token_limit=quota.token_limit,
            token_used=token_used,
            rate_limit=quota.rate_limit,
            current_usage_state=current_usage_state,
            quota_status=quota_status,
        )


competition_manager_service = CompetitionManagerService()
