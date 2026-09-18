import pytest
import asyncio
import uuid
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import get_db, Base
import backend.core.database as core_db
import backend.services.execution_log_service as log_service
import backend.services.model_gateway as model_gateway
import backend.services.competition_manager_service as comp_service
import backend.services.authorization_service as authz_service
import backend.services.langgraph_execution_strategy as langgraph_strategy
from backend.models.orm import Team, TeamQuota, TeamMember

# Prefer a deterministic local sqlite test DB to avoid external role/config dependencies.
TEST_DB_URL = os.getenv("AGENTFORGE_TEST_DB_URL", "sqlite+aiosqlite:///./.agentforge_test.db")

# Use NullPool for tests to avoid "another operation is in progress" issues
test_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# CRITICAL: Override global database objects in ALL relevant modules
core_db.engine = test_engine
core_db.AsyncSessionLocal = TestingSessionLocal
log_service.AsyncSessionLocal = TestingSessionLocal
model_gateway.AsyncSessionLocal = TestingSessionLocal
comp_service.AsyncSessionLocal = TestingSessionLocal
authz_service.AsyncSessionLocal = TestingSessionLocal
langgraph_strategy.AsyncSessionLocal = TestingSessionLocal

# Test constants
TEST_TEAM_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_TEAM_B_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
TEST_TEAM_NAME = "Test Team"
TEST_USERS = ["user-integration", "user-e2e", "user1", "user-quota", "user-team-a-2"]
TEST_TEAM_B_USERS = ["user-team-b-1"]

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
async def setup_database():
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        # Seed mandatory test data
        async with TestingSessionLocal() as session:
            test_team = Team(id=TEST_TEAM_ID, name=TEST_TEAM_NAME, status="ACTIVE")
            test_team_b = Team(id=TEST_TEAM_B_ID, name="Test Team B", status="ACTIVE")
            test_quota = TeamQuota(team_id=TEST_TEAM_ID, token_limit=1000000, rate_limit=100)
            test_quota_b = TeamQuota(team_id=TEST_TEAM_B_ID, token_limit=1000000, rate_limit=100)
            session.add(test_team)
            session.add(test_team_b)
            session.add(test_quota)
            session.add(test_quota_b)
            for user_id in TEST_USERS:
                session.add(
                    TeamMember(
                        team_id=TEST_TEAM_ID,
                        user_id=user_id,
                        role="member",
                        status="ACTIVE",
                    )
                )
            for user_id in TEST_TEAM_B_USERS:
                session.add(
                    TeamMember(
                        team_id=TEST_TEAM_B_ID,
                        user_id=user_id,
                        role="member",
                        status="ACTIVE",
                    )
                )
            await session.commit()
            
        yield
    except Exception as e:
        print(f"Failed to setup test database: {e}")
        yield
    finally:
        try:
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        except Exception:
            pass

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
def client() -> TestClient:
    # Use TestClient without 'with' block to avoid startup/lifespan conflicts with setup_database
    return TestClient(app)
