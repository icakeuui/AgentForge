import uuid
from typing import Optional

from sqlalchemy import select

from backend.core.database import AsyncSessionLocal
from backend.core.exceptions import PermissionException
from backend.core.logging import logger
from backend.models.constants import ResponseCode
from backend.models.orm import AgentOwnership, ExecutionLog, Team, TeamMember
from backend.models.schemas import AuthContext
from plugin_marketplace.db import PMUserExtension


class AuthorizationService:
    async def validate_membership(self, auth: AuthContext) -> None:
        if auth.is_dev and auth.auth_mode == "dev_bypass":
            return
        if not auth.user_id or not auth.team_id:
            self._deny("membership", auth, "Missing user_id or team_id")

        try:
            team_uuid = uuid.UUID(auth.team_id)
        except ValueError:
            self._deny("membership", auth, f"Invalid team_id: {auth.team_id}")

        async with AsyncSessionLocal() as session:
            team_res = await session.execute(select(Team).where(Team.id == team_uuid))
            team = team_res.scalar_one_or_none()
            if not team or team.status != "ACTIVE":
                self._deny("membership", auth, f"Team not active: {auth.team_id}")

            await self._ensure_user_membership(session, team_uuid, auth.user_id, auth, "membership")

    async def ensure_team_scope(self, auth: AuthContext, target_team_id: str, resource_type: str) -> None:
        if auth.team_id != target_team_id:
            self._deny(
                resource_type,
                auth,
                f"Cross-team access denied: auth_team={auth.team_id}, target_team={target_team_id}",
            )

    async def ensure_agent_ownership(self, auth: AuthContext, agent_id: uuid.UUID, operation: str) -> None:
        async with AsyncSessionLocal() as session:
            ownership_res = await session.execute(
                select(AgentOwnership).where(AgentOwnership.agent_id == agent_id)
            )
            ownership = ownership_res.scalar_one_or_none()
            if ownership is None:
                self._deny("agent", auth, f"Missing ownership mapping for agent={agent_id}")

            owner_team_id = str(ownership.team_id)
            if owner_team_id != auth.team_id:
                self._deny(
                    "agent",
                    auth,
                    f"Agent ownership denied for {operation}: agent={agent_id}, owner_team={owner_team_id}",
                )

    async def ensure_execution_record_ownership(self, auth: AuthContext, execution_id: uuid.UUID) -> None:
        async with AsyncSessionLocal() as session:
            execution_res = await session.execute(
                select(ExecutionLog).where(ExecutionLog.execution_id == execution_id)
            )
            execution = execution_res.scalar_one_or_none()
            if execution is None:
                self._deny("execution_record", auth, f"Execution record not found: {execution_id}")

            owner_team_id = str(execution.team_id)
            if owner_team_id != auth.team_id:
                self._deny(
                    "execution_record",
                    auth,
                    f"Execution record ownership denied: execution_id={execution_id}, owner_team={owner_team_id}",
                )

    async def ensure_quota_context_ownership(self, auth: AuthContext, team_id: str) -> None:
        async with AsyncSessionLocal() as session:
            try:
                team_uuid = uuid.UUID(team_id)
            except ValueError:
                self._deny("runtime_quota_context", auth, f"Invalid team id: {team_id}")
                return

            team_res = await session.execute(select(Team).where(Team.id == team_uuid))
            team = team_res.scalar_one_or_none()
            if not team or team.status != "ACTIVE":
                self._deny("runtime_quota_context", auth, f"Team not active: {team_id}")
            await self.ensure_team_scope(auth, team_id, "runtime_quota_context")

    async def ensure_extension_installation_scope(
        self, auth: AuthContext, target_user_id: str, extension_id: str
    ) -> None:
        async with AsyncSessionLocal() as session:
            team_uuid = uuid.UUID(auth.team_id)
            await self._ensure_user_membership(
                session,
                team_uuid,
                target_user_id,
                auth,
                "extension_installation",
            )

    async def ensure_user_extension_ownership(
        self, auth: AuthContext, target_user_id: str, extension_id: str
    ) -> None:
        async with AsyncSessionLocal() as session:
            team_uuid = uuid.UUID(auth.team_id)
            await self._ensure_user_membership(
                session,
                team_uuid,
                target_user_id,
                auth,
                "extension_installation",
            )

            ue_res = await session.execute(
                select(PMUserExtension).where(
                    PMUserExtension.user_id == target_user_id,
                    PMUserExtension.extension_id == extension_id,
                )
            )
            ue = ue_res.scalar_one_or_none()
            if ue is None:
                self._deny(
                    "extension_installation",
                    auth,
                    f"Extension record not found for user={target_user_id}, extension={extension_id}",
                )

    async def _ensure_user_membership(
        self,
        session,
        team_uuid: uuid.UUID,
        user_id: str,
        auth: AuthContext,
        resource_type: str,
    ) -> None:
        member_res = await session.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_uuid,
                TeamMember.user_id == user_id,
                TeamMember.status == "ACTIVE",
            )
        )
        member = member_res.scalar_one_or_none()
        if member is None:
            self._deny(
                resource_type,
                auth,
                f"Membership validation failed for user={user_id}, team={team_uuid}",
            )

    def _deny(self, resource_type: str, auth: AuthContext, reason: str) -> None:
        if resource_type == "membership":
            log_message = f"membership validation failed log: {reason}"
        else:
            log_message = f"permission denied log: resource ownership denied log: {reason}"
        logger.bind(
            resource_type=resource_type,
            resource_id="*",
        ).warning(log_message)
        raise PermissionException(reason, code=ResponseCode.TEAM_FORBIDDEN)


authorization_service = AuthorizationService()
