import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.core.database import Base

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        primary_key=True, 
        default=uuid.uuid4
    )
    config: Mapped[dict] = mapped_column(JSON, nullable=False)

    def __repr__(self) -> str:
        return f"<Agent(id={self.id})>"

class AgentOwnership(Base):
    __tablename__ = "agent_ownerships"

    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<AgentOwnership(agent_id={self.agent_id}, team_id={self.team_id})>"


class PublishedAgent(Base):
    __tablename__ = "published_agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True, index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<PublishedAgent(agent_id={self.agent_id}, slug={self.slug}, status={self.status})>"

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    document_type: Mapped[str] = mapped_column(nullable=False, default="other")
    source_filename: Mapped[Optional[str]] = mapped_column(nullable=True)
    source_mime_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    source_hash: Mapped[Optional[str]] = mapped_column(nullable=True)
    version_label: Mapped[Optional[str]] = mapped_column(nullable=True)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(nullable=False, default="ACTIVE")
    embedding_status: Mapped[str] = mapped_column(nullable=False, default="pending")
    embedding_provider: Mapped[Optional[str]] = mapped_column(nullable=True)
    embedding_model_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    embedding_dimensions: Mapped[Optional[int]] = mapped_column(nullable=True)
    embedding_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding_status: Mapped[str] = mapped_column(nullable=False, default="pending")
    embedding_provider: Mapped[Optional[str]] = mapped_column(nullable=True)
    embedding_model_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    embedding_dimensions: Mapped[Optional[int]] = mapped_column(nullable=True)
    embedding_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    document_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<KnowledgeDocument(id={self.id}, agent_id={self.agent_id})>"

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    token_text: Mapped[str] = mapped_column(nullable=False, default="")
    chunk_type: Mapped[str] = mapped_column(nullable=False, default="plain")
    section_path: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    article_no: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)
    article_label: Mapped[Optional[str]] = mapped_column(nullable=True)
    page_no: Mapped[Optional[int]] = mapped_column(nullable=True)
    start_char: Mapped[Optional[int]] = mapped_column(nullable=True)
    end_char: Mapped[Optional[int]] = mapped_column(nullable=True)
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    embedding: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    embedding_status: Mapped[str] = mapped_column(nullable=False, default="pending")
    embedding_model_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    embedding_dimensions: Mapped[Optional[int]] = mapped_column(nullable=True)
    vector_point_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    embedding_status: Mapped[str] = mapped_column(nullable=False, default="pending")
    embedding_model_name: Mapped[Optional[str]] = mapped_column(nullable=True)
    embedding_dimensions: Mapped[Optional[int]] = mapped_column(nullable=True)
    vector_point_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<KnowledgeChunk(document_id={self.document_id}, chunk_index={self.chunk_index})>"

class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    execution_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(nullable=False, index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    status: Mapped[str] = mapped_column(nullable=False)
    final_state: Mapped[str] = mapped_column(nullable=False)
    termination_reason: Mapped[str] = mapped_column(nullable=False)
    steps_used: Mapped[int] = mapped_column(default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    final_answer: Mapped[Optional[str]] = mapped_column(nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    error_source: Mapped[Optional[str]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(nullable=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<ExecutionLog(id={self.execution_id}, status={self.status})>"

class ReactStepLog(Base):
    __tablename__ = "react_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(nullable=False)
    request_id: Mapped[str] = mapped_column(nullable=False)
    step_status: Mapped[str] = mapped_column(nullable=False)
    state_before: Mapped[Optional[str]] = mapped_column(nullable=True)
    state_after: Mapped[Optional[str]] = mapped_column(nullable=True)
    thought: Mapped[Optional[str]] = mapped_column(nullable=True)
    action: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    observation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    error_source: Mapped[Optional[str]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<ReactStepLog(execution_id={self.execution_id}, step={self.step_index})>"

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, 
        primary_key=True, 
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="ACTIVE") # ACTIVE / DISABLED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name}, status={self.status})>"

class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(nullable=False, index=True)
    role: Mapped[str] = mapped_column(nullable=False, default="member")
    status: Mapped[str] = mapped_column(nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<TeamMember(team_id={self.team_id}, user_id={self.user_id}, status={self.status})>"

class TeamQuota(Base):
    __tablename__ = "team_quotas"

    team_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    token_limit: Mapped[int] = mapped_column(nullable=False)
    rate_limit: Mapped[int] = mapped_column(nullable=False)

    def __repr__(self) -> str:
        return f"<TeamQuota(team_id={self.team_id}, token_limit={self.token_limit})>"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    search_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email={self.email}, status={self.status})>"


class UserCredential(Base):
    __tablename__ = "user_credentials"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    password_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<UserCredential(user_id={self.user_id})>"


class SearchIdAllocation(Base):
    __tablename__ = "search_id_allocations"

    search_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<SearchIdAllocation(search_id={self.search_id}, user_id={self.user_id})>"


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    send_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    send_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_send_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<EmailVerificationCode(email={self.email}, purpose={self.purpose}, status={self.send_status})>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<RefreshToken(user_id={self.user_id}, revoked={self.revoked_at is not None})>"
