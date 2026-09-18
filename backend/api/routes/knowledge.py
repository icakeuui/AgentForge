import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_current_user
from backend.core.database import get_db
from backend.core.exceptions import NotFoundException, ValidationException
from backend.models.schemas import (
    AuthContext,
    BaseResponse,
    KnowledgeDocumentCreateRequest,
    KnowledgeDocumentRead,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
)
from backend.services.agent_service import AgentService
from backend.services.authorization_service import authorization_service
from backend.services.knowledge_service import knowledge_service
from backend.services.knowledge_ingestion_service import knowledge_ingestion_service

router = APIRouter(prefix="/agents/{agent_id}/knowledge", tags=["Knowledge"])


async def _ensure_agent_access(db: AsyncSession, auth: AuthContext, agent_id: uuid.UUID) -> None:
    agent = await AgentService.get_agent(db, agent_id)
    if agent is None:
        raise NotFoundException(f"Agent with ID {agent_id} not found")
    await authorization_service.ensure_agent_ownership(auth, agent_id, operation="read")


@router.get("", response_model=BaseResponse[list[KnowledgeDocumentRead]])
async def list_knowledge_documents(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await _ensure_agent_access(db, auth, agent_id)
    documents = await knowledge_service.list_documents(
        db,
        agent_id=agent_id,
        team_id=uuid.UUID(auth.team_id),
    )
    return BaseResponse.success(data=documents, message="OK")


@router.post("", response_model=BaseResponse[KnowledgeDocumentRead])
async def create_knowledge_document(
    agent_id: uuid.UUID,
    payload: KnowledgeDocumentCreateRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await _ensure_agent_access(db, auth, agent_id)
    document = await knowledge_service.create_document(
        db,
        agent_id=agent_id,
        team_id=uuid.UUID(auth.team_id),
        title=payload.title,
        content=payload.content,
    )
    return BaseResponse.success(data=document, message="Created successfully")


@router.post("/upload", response_model=BaseResponse[KnowledgeDocumentRead])
async def upload_knowledge_document(
    agent_id: uuid.UUID,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await _ensure_agent_access(db, auth, agent_id)
    raw_data = await file.read()
    try:
        extracted_title, content = knowledge_service.extract_uploaded_content(
            filename=file.filename or "未命名文件",
            content_type=file.content_type,
            data=raw_data,
        )
    except (ValueError, RuntimeError) as exc:
        raise ValidationException(str(exc)) from exc
    document = await knowledge_service.create_document(
        db,
        agent_id=agent_id,
        team_id=uuid.UUID(auth.team_id),
        title=(title or "").strip() or extracted_title,
        content=content,
        source_filename=file.filename,
        source_mime_type=file.content_type,
    )
    ingestion = await knowledge_ingestion_service.ingest_document(
        db,
        document_id=document.id,
        agent_id=agent_id,
    )
    document.embedding_status = ingestion.status
    document.embedding_provider = ingestion.provider
    document.embedding_model_name = ingestion.model
    document.embedding_dimensions = ingestion.dimensions
    document.embedding_error = ingestion.error
    document.embedded_chunk_count = ingestion.embedded_chunk_count
    return BaseResponse.success(data=document, message="Uploaded successfully")


@router.post("/search", response_model=BaseResponse[list[KnowledgeSearchResult]])
async def search_knowledge(
    agent_id: uuid.UUID,
    payload: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await _ensure_agent_access(db, auth, agent_id)
    results = await knowledge_service.search(
        db,
        agent_id=agent_id,
        team_id=uuid.UUID(auth.team_id),
        query=payload.query,
        limit=payload.limit,
        retrieval_mode=payload.retrieval_mode,
        article_no=payload.article_no,
        include_near_misses=payload.include_near_misses,
        document_type=payload.document_type,
    )
    return BaseResponse.success(data=results, message="OK")


@router.delete("/{document_id}", response_model=BaseResponse[dict])
async def delete_knowledge_document(
    agent_id: uuid.UUID,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await _ensure_agent_access(db, auth, agent_id)
    deleted = await knowledge_service.delete_document(
        db,
        agent_id=agent_id,
        team_id=uuid.UUID(auth.team_id),
        document_id=document_id,
    )
    if not deleted:
        raise NotFoundException(f"Knowledge document with ID {document_id} not found")
    return BaseResponse.success(data={"deleted": True}, message="Deleted successfully")
