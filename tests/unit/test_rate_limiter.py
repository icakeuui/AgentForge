import pytest
from unittest.mock import AsyncMock, patch
from backend.core.rate_limiter import RateLimiter, LimitStatus

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_rate_limiter_check_rate_limit(mock_redis):
    limiter = RateLimiter("redis://localhost:6379/1")
    limiter._redis = mock_redis
    
    # Under limit
    mock_redis.incr.return_value = 5  # under limit 10
    status = await limiter.check_rate_limit("team1", qps_limit=10)
    assert status == LimitStatus.ALLOWED
    
    # Over limit
    mock_redis.incr.return_value = 11  # over limit 10
    status = await limiter.check_rate_limit("team1", qps_limit=10)
    assert status == LimitStatus.EXCEEDED

@pytest.mark.asyncio
async def test_rate_limiter_check_token_limit(mock_redis):
    limiter = RateLimiter("redis://localhost:6379/1")
    limiter._redis = mock_redis
    
    # Under limit
    mock_redis.get.return_value = "50"
    status = await limiter.check_token_limit("team1", token_limit=100)
    assert status == LimitStatus.ALLOWED
    
    # Over limit
    mock_redis.get.return_value = "100"
    status = await limiter.check_token_limit("team1", token_limit=100)
    assert status == LimitStatus.EXCEEDED
    
    # No usage
    mock_redis.get.return_value = None
    status = await limiter.check_token_limit("team1", token_limit=100)
    assert status == LimitStatus.ALLOWED

@pytest.mark.asyncio
async def test_rate_limiter_add_token_usage(mock_redis):
    limiter = RateLimiter("redis://localhost:6379/1")
    limiter._redis = mock_redis
    
    await limiter.add_token_usage("team1", 20)
    mock_redis.incrby.assert_called_with("token_usage:team1", 20)
