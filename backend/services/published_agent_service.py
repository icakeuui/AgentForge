import re
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import NotFoundException, ValidationException
from backend.models.orm import PublishedAgent
from backend.models.schemas import AgentRead, PublicAgentProfile, PublishedAgentRead, PublishedAgentUpsertRequest


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PublishedAgentService:
    @staticmethod
    def _normalize_slug(value: str) -> str:
        slug = value.strip().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        if not slug:
            slug = f"agent-{uuid.uuid4().hex[:8]}"
        if len(slug) > 80:
            slug = slug[:80].strip("-")
        if not SLUG_RE.match(slug):
            raise ValidationException("Slug must contain lowercase letters, numbers, and hyphens only")
        return slug

    @staticmethod
    def _default_slug(agent: AgentRead) -> str:
        return PublishedAgentService._normalize_slug(agent.name or f"agent-{agent.id}")

    @staticmethod
    def _to_read(record: PublishedAgent) -> PublishedAgentRead:
        return PublishedAgentRead(
            id=record.id,
            agent_id=record.agent_id,
            team_id=str(record.team_id),
            slug=record.slug,
            title=record.title,
            description=record.description,
            status=record.status,
            public_url=f"/p/{record.slug}",
            created_at=record.created_at.isoformat() if record.created_at else "",
            updated_at=record.updated_at.isoformat() if record.updated_at else "",
        )

    @staticmethod
    async def get_by_agent(db: AsyncSession, agent_id: uuid.UUID, team_id: uuid.UUID) -> Optional[PublishedAgentRead]:
        result = await db.execute(
            select(PublishedAgent).where(PublishedAgent.agent_id == agent_id, PublishedAgent.team_id == team_id)
        )
        record = result.scalar_one_or_none()
        return PublishedAgentService._to_read(record) if record else None

    @staticmethod
    async def get_active_record_by_slug(db: AsyncSession, slug: str) -> PublishedAgent:
        result = await db.execute(
            select(PublishedAgent).where(PublishedAgent.slug == slug.strip().lower(), PublishedAgent.status == "ACTIVE")
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundException(f"Published agent with slug {slug} not found")
        return record

    @staticmethod
    async def list_active_records(db: AsyncSession) -> list[PublishedAgent]:
        result = await db.execute(
            select(PublishedAgent)
            .where(PublishedAgent.status == "ACTIVE")
            .order_by(PublishedAgent.updated_at.desc(), PublishedAgent.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_public_profile(db: AsyncSession, slug: str, agent: AgentRead) -> PublicAgentProfile:
        record = await PublishedAgentService.get_active_record_by_slug(db, slug)
        return PublicAgentProfile(
            slug=record.slug,
            title=record.title,
            description=record.description,
            opening_statement=agent.opening_statement,
            avatar_url=agent.avatar_url,
        )

    @staticmethod
    async def upsert(
        db: AsyncSession,
        *,
        agent: AgentRead,
        team_id: uuid.UUID,
        payload: PublishedAgentUpsertRequest,
    ) -> PublishedAgentRead:
        result = await db.execute(
            select(PublishedAgent).where(PublishedAgent.agent_id == agent.id, PublishedAgent.team_id == team_id)
        )
        record = result.scalar_one_or_none()
        next_slug = PublishedAgentService._normalize_slug(payload.slug) if payload.slug else None
        if record is None:
            next_slug = next_slug or PublishedAgentService._default_slug(agent)
        elif next_slug is None:
            next_slug = record.slug

        conflict_result = await db.execute(
            select(PublishedAgent).where(PublishedAgent.slug == next_slug, PublishedAgent.agent_id != agent.id)
        )
        if conflict_result.scalar_one_or_none() is not None:
            raise ValidationException("Slug is already in use")

        if record is None:
            record = PublishedAgent(
                agent_id=agent.id,
                team_id=team_id,
                slug=next_slug,
                title=(payload.title or agent.name).strip(),
                description=(payload.description if payload.description is not None else agent.description).strip(),
                status=payload.status or "ACTIVE",
            )
            db.add(record)
        else:
            record.slug = next_slug
            if payload.title is not None:
                record.title = payload.title.strip()
            if payload.description is not None:
                record.description = payload.description.strip()
            if payload.status is not None:
                record.status = payload.status
            else:
                record.status = "ACTIVE"

        await db.commit()
        await db.refresh(record)
        return PublishedAgentService._to_read(record)

    @staticmethod
    async def disable(db: AsyncSession, *, agent_id: uuid.UUID, team_id: uuid.UUID) -> PublishedAgentRead:
        result = await db.execute(
            select(PublishedAgent).where(PublishedAgent.agent_id == agent_id, PublishedAgent.team_id == team_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundException(f"Publication for agent {agent_id} not found")
        record.status = "DISABLED"
        await db.commit()
        await db.refresh(record)
        return PublishedAgentService._to_read(record)


published_agent_service = PublishedAgentService()
