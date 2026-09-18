from enum import Enum
import time
from typing import Optional
from redis.asyncio import Redis, ConnectionPool
from backend.core.config import settings
from backend.core.logging import logger

class LimitStatus(Enum):
    ALLOWED = "ALLOWED"
    EXCEEDED = "EXCEEDED"
    INFRA_ERROR = "INFRA_ERROR"

class RateLimiter:
    def __init__(self, redis_url: str):
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None
        self.redis_url = redis_url

    async def connect(self) -> bool:
        """
        Initialize Redis connection pool and client.
        Returns False if connection fails.
        """
        try:
            if not self._redis:
                self._pool = ConnectionPool.from_url(self.redis_url, decode_responses=True)
                self._redis = Redis(connection_pool=self._pool)
                # Ping to verify connection
                await self._redis.ping()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            return False

    async def check_rate_limit(self, team_id: str, qps_limit: int = 5) -> LimitStatus:
        """
        Check if the team has exceeded the QPS limit.
        """
        if not await self.connect():
            return LimitStatus.INFRA_ERROR

        current_ts = int(time.time())
        key = f"rate_limit:{team_id}:{current_ts}"
        
        try:
            count = await self._redis.incr(key)
            if count == 1:
                await self._redis.expire(key, 2)
            
            if count > qps_limit:
                logger.warning(f"Rate limit exceeded for team {team_id}: {count}/{qps_limit}")
                return LimitStatus.EXCEEDED
            return LimitStatus.ALLOWED
        except Exception as e:
            logger.error(f"Rate limiter execution error: {str(e)}")
            return LimitStatus.INFRA_ERROR

    async def check_token_limit(self, team_id: str, token_limit: int) -> LimitStatus:
        """
        Check if the team has exceeded the total token limit.
        """
        if not await self.connect():
            return LimitStatus.INFRA_ERROR

        key = f"token_usage:{team_id}"
        
        try:
            current_usage = await self._redis.get(key)
            if current_usage and int(current_usage) >= token_limit:
                logger.warning(f"Token limit exceeded for team {team_id}: {current_usage}/{token_limit}")
                return LimitStatus.EXCEEDED
            return LimitStatus.ALLOWED
        except Exception as e:
            logger.error(f"Token limit check error: {str(e)}")
            return LimitStatus.INFRA_ERROR

    async def add_token_usage(self, team_id: str, tokens: int):
        """
        Accumulate token usage for the team.
        """
        if not await self.connect():
            return

        key = f"token_usage:{team_id}"
        try:
            # Atomic increment
            await self._redis.incrby(key, tokens)
        except Exception as e:
            logger.error(f"Add token usage error: {str(e)}")

    async def get_token_usage(self, team_id: str) -> Optional[int]:
        if not await self.connect():
            return None
        key = f"token_usage:{team_id}"
        try:
            value = await self._redis.get(key)
            if value is None:
                return 0
            return int(value)
        except Exception as e:
            logger.error(f"Get token usage error: {str(e)}")
            return None

    async def get_current_rate_usage(self, team_id: str) -> Optional[int]:
        if not await self.connect():
            return None
        current_ts = int(time.time())
        key = f"rate_limit:{team_id}:{current_ts}"
        try:
            value = await self._redis.get(key)
            if value is None:
                return 0
            return int(value)
        except Exception as e:
            logger.error(f"Get current rate usage error: {str(e)}")
            return None

rate_limiter = RateLimiter(settings.REDIS_URL)
