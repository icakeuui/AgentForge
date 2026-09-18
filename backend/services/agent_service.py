import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models.orm import Agent, AgentOwnership
from backend.models.schemas import AgentCreateRequest, AgentRead, AgentUpdateRequest
from backend.core.security import encrypt_api_key, validate_provider_url

class AgentService:
    DEFAULT_OPENING_STATEMENT = "你好，我是你的智能体。你可以直接告诉我想测试的问题或任务。"

    @staticmethod
    def _extract_string(value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    @staticmethod
    def _is_string_list(value: object) -> bool:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)

    @staticmethod
    def _compose_agent_read(db_agent: Agent) -> AgentRead:
        cfg = db_agent.config if isinstance(db_agent.config, dict) else {}
        runtime_config = cfg.get("runtime_config") if isinstance(cfg.get("runtime_config"), dict) else {}
        capability_flags = cfg.get("capability_flags") if isinstance(cfg.get("capability_flags"), dict) else {}
        tools = cfg.get("tools") if AgentService._is_string_list(cfg.get("tools")) else []
        constraints = cfg.get("constraints") if isinstance(cfg.get("constraints"), dict) else {"max_steps": 6}
        name = AgentService._extract_string(cfg.get("name"))
        llm_model_name = AgentService._extract_string(cfg.get("llm_model_name"))
        archived = bool(cfg.get("archived", False))
        embedding_cfg = cfg.get("embedding") if isinstance(cfg.get("embedding"), dict) else None
        embedding_read = None
        if embedding_cfg is not None:
            embedding_read = {
                "provider": AgentService._extract_string(embedding_cfg.get("provider")) or "openai_compatible",
                "base_url": AgentService._extract_string(embedding_cfg.get("base_url")),
                "model": AgentService._extract_string(embedding_cfg.get("model")),
                "has_api_key": bool(embedding_cfg.get("api_key_encrypted")),
            }

        availability_reason: Optional[str] = None
        is_available = True
        if not isinstance(db_agent.config, dict):
            is_available = False
            availability_reason = "Invalid legacy config"
        elif llm_model_name == "":
            is_available = False
            availability_reason = "Missing model configuration"
        elif archived:
            is_available = False
            availability_reason = "Archived"

        return AgentRead(
            id=db_agent.id,
            name=name if name else "Untitled Agent",
            description=AgentService._extract_string(cfg.get("description")),
            opening_statement=AgentService._extract_string(cfg.get("opening_statement")) or AgentService.DEFAULT_OPENING_STATEMENT,
            avatar_url=cfg.get("avatar_url") if isinstance(cfg.get("avatar_url"), str) else None,
            llm_provider_url=AgentService._extract_string(cfg.get("llm_provider_url")),
            llm_model_name=llm_model_name,
            runtime_config={
                "temperature": runtime_config.get("temperature", 0.7),
                "max_tokens": runtime_config.get("max_tokens"),
                "context_window": runtime_config.get("context_window"),
                "reserved_completion_tokens": runtime_config.get("reserved_completion_tokens"),
            },
            capability_flags={
                "supports_tools": bool(capability_flags.get("supports_tools", True)),
            },
            tools=tools,
            constraints=constraints,
            has_api_key=bool(cfg.get("llm_api_key_encrypted")),
            archived=archived,
            is_available=is_available,
            availability_reason=availability_reason,
            embedding=embedding_read,
        )

    @staticmethod
    def _to_agent_read(db_agent: Agent) -> AgentRead:
        return AgentService._compose_agent_read(db_agent)

    @staticmethod
    async def create_agent(db: AsyncSession, config: AgentCreateRequest, team_id: str) -> AgentRead:
        validate_provider_url(config.llm_provider_url)
        agent_data = config.model_dump(mode="json")
        agent_data["llm_api_key_encrypted"] = encrypt_api_key(config.llm_api_key)
        agent_data.pop("llm_api_key", None)
        embedding = agent_data.get("embedding")
        if isinstance(embedding, dict):
            api_key = embedding.pop("api_key", None)
            if api_key:
                embedding["api_key_encrypted"] = encrypt_api_key(api_key)
            else:
                embedding.pop("api_key_encrypted", None)

        db_agent = Agent(
            id=uuid.uuid4(),
            config=agent_data
        )
        db.add(db_agent)
        db.add(
            AgentOwnership(
                agent_id=db_agent.id,
                team_id=uuid.UUID(team_id),
            )
        )
        await db.commit()
        await db.refresh(db_agent)
        return AgentService._to_agent_read(db_agent)

    @staticmethod
    async def list_agents(db: AsyncSession, team_id: str) -> List[AgentRead]:
        ownership_stmt = select(AgentOwnership.agent_id).where(AgentOwnership.team_id == uuid.UUID(team_id))
        ownership_rows = await db.execute(ownership_stmt)
        agent_ids = [row[0] for row in ownership_rows.fetchall()]
        if not agent_ids:
            return []
        agent_stmt = select(Agent).where(Agent.id.in_(agent_ids))
        rows = await db.execute(agent_stmt)
        agents = rows.scalars().all()
        normalized: List[AgentRead] = []
        for agent in agents:
            normalized.append(AgentService._to_agent_read(agent))
        return normalized

    @staticmethod
    async def get_agent(db: AsyncSession, agent_id: uuid.UUID) -> Optional[AgentRead]:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        db_agent = result.scalar_one_or_none()
        
        if db_agent:
            return AgentService._to_agent_read(db_agent)
        return None

    @staticmethod
    async def get_agent_raw(db: AsyncSession, agent_id: uuid.UUID) -> Optional[Agent]:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_agent(db: AsyncSession, agent_id: uuid.UUID, payload: AgentUpdateRequest) -> Optional[AgentRead]:
        db_agent = await AgentService.get_agent_raw(db, agent_id)
        if db_agent is None:
            return None

        next_config = dict(db_agent.config or {})
        incoming = payload.model_dump(exclude_none=True, mode="json")
        if "llm_provider_url" in incoming:
            validate_provider_url(incoming["llm_provider_url"])
        if "llm_api_key" in incoming:
            incoming["llm_api_key_encrypted"] = encrypt_api_key(incoming.pop("llm_api_key"))
        embedding = incoming.get("embedding")
        if isinstance(embedding, dict):
            embedding = dict(embedding)
            api_key = embedding.pop("api_key", None)
            if api_key:
                embedding["api_key_encrypted"] = encrypt_api_key(api_key)
            else:
                existing = next_config.get("embedding") if isinstance(next_config.get("embedding"), dict) else {}
                if existing.get("api_key_encrypted"):
                    embedding["api_key_encrypted"] = existing["api_key_encrypted"]
            incoming["embedding"] = embedding

        next_config.update(incoming)
        db_agent.config = next_config
        await db.commit()
        await db.refresh(db_agent)
        return AgentService._to_agent_read(db_agent)

    @staticmethod
    async def delete_agent(db: AsyncSession, agent_id: uuid.UUID) -> Optional[AgentRead]:
        db_agent = await AgentService.get_agent_raw(db, agent_id)
        if db_agent is None:
            return None
        next_config = dict(db_agent.config or {})
        next_config["archived"] = True
        db_agent.config = next_config
        await db.commit()
        await db.refresh(db_agent)
        return AgentService._to_agent_read(db_agent)

    @staticmethod
    async def get_agent_owner_team_id(db: AsyncSession, agent_id: uuid.UUID) -> Optional[str]:
        result = await db.execute(
            select(AgentOwnership).where(AgentOwnership.agent_id == agent_id)
        )
        ownership = result.scalar_one_or_none()
        if ownership is None:
            return None
        return str(ownership.team_id)

# Global instance
agent_service = AgentService()
