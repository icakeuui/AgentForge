import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api.dependencies import get_current_user
from backend.core.database import get_db
import backend.core.database as database_module
from backend.core.config import PROJECT_ROOT
from backend.core.exceptions import NotFoundException, ValidationException
from backend.models.orm import KnowledgeDocument
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
from backend.services.rag_retrieval_service import rag_retrieval_service
from backend.core.logging import logger
from backend.services.knowledge_ingestion_service import knowledge_ingestion_service

router = APIRouter(prefix="/agents/{agent_id}/knowledge", tags=["Knowledge"])
BACKGROUND_INDEX_CHUNK_THRESHOLD = 32
BACKGROUND_PARSE_FILE_THRESHOLD = 8 * 1024 * 1024
STAGED_UPLOAD_DIR = PROJECT_ROOT / "data" / "knowledge_jobs"
ACTIVE_INDEX_JOBS: set[uuid.UUID] = set()


async def _index_in_background(document_id: uuid.UUID, agent_id: uuid.UUID) -> None:
    """Use a fresh session after the upload response has closed its session."""
    try:
        async with database_module.AsyncSessionLocal() as db:
            try:
                await knowledge_ingestion_service.ingest_document(
                    db, document_id=document_id, agent_id=agent_id,
                )
            except Exception as exc:
                document = await db.get(KnowledgeDocument, document_id)
                if document is not None:
                    document.status = "FAILED"
                    document.embedding_status = "failed"
                    document.embedding_error = f"{type(exc).__name__}: {exc}"[:2000]
                    await db.commit()
                logger.exception("Background knowledge indexing failed for {}", document_id)
    finally:
        ACTIVE_INDEX_JOBS.discard(document_id)


async def _process_staged_upload(document_id: uuid.UUID, agent_id: uuid.UUID) -> None:
    """Parse a durable raw upload, then index its stable document/chunk IDs."""
    try:
        async with database_module.AsyncSessionLocal() as db:
            document = await db.get(KnowledgeDocument, document_id)
            if document is None or document.agent_id != agent_id:
                return
            raw_path = STAGED_UPLOAD_DIR / f"{document_id}.bin"
            raw_data = await asyncio.to_thread(raw_path.read_bytes)
            _title, content = await asyncio.to_thread(
                knowledge_service.extract_uploaded_content,
                filename=document.source_filename or document.title,
                content_type=document.source_mime_type,
                data=raw_data,
            )
            await knowledge_service.populate_staged_document(db, document=document, content=content)
        await _index_in_background(document_id, agent_id)
    except Exception as exc:
        async with database_module.AsyncSessionLocal() as db:
            document = await db.get(KnowledgeDocument, document_id)
            if document is not None:
                document.status = "FAILED"
                document.embedding_status = "failed"
                document.embedding_error = f"{type(exc).__name__}: {exc}"[:2000]
                await db.commit()
        logger.exception("Staged knowledge parsing failed for {}", document_id)
    finally:
        ACTIVE_INDEX_JOBS.discard(document_id)


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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await _ensure_agent_access(db, auth, agent_id)
    raw_data = await file.read()
    if len(raw_data) > knowledge_service.MAX_UPLOAD_BYTES:
        raise ValidationException("文件过大，请上传 100MB 以内的文件")
    if not raw_data:
        raise ValidationException("上传文件为空")
    filename = file.filename or "未命名文件"
    if len(raw_data) > BACKGROUND_PARSE_FILE_THRESHOLD:
        extension = Path(filename).suffix.lower()
        if extension not in knowledge_service.SUPPORTED_UPLOAD_EXTENSIONS:
            raise ValidationException("仅支持 PDF、Word（.docx）或 TXT 文件")
        raw_hash = hashlib.sha256(raw_data).hexdigest()
        existing = await db.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.agent_id == agent_id,
                KnowledgeDocument.team_id == uuid.UUID(auth.team_id),
                KnowledgeDocument.source_filename == filename,
                KnowledgeDocument.source_hash == raw_hash,
            ).order_by(KnowledgeDocument.created_at.desc()).limit(1)
        )
        if existing is not None:
            return BaseResponse.success(
                data=knowledge_service._read_model(existing, chunk_count=existing.chunk_count),
                message="Document already uploaded",
            )
        document_id = uuid.uuid4()
        STAGED_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread((STAGED_UPLOAD_DIR / f"{document_id}.bin").write_bytes, raw_data)
        staged = KnowledgeDocument(
            id=document_id, agent_id=agent_id, team_id=uuid.UUID(auth.team_id),
            title=(title or "").strip() or filename, content="", document_type="other",
            source_filename=filename, source_mime_type=file.content_type,
            source_hash=raw_hash, status="PROCESSING", embedding_status="processing",
            chunk_count=0,
            document_metadata={"upload_job_version": 1, "processing_stage": "parsing_or_ocr"},
        )
        db.add(staged)
        await db.commit()
        await db.refresh(staged)
        ACTIVE_INDEX_JOBS.add(document_id)
        background_tasks.add_task(_process_staged_upload, document_id, agent_id)
        return BaseResponse.success(
            data=knowledge_service._read_model(staged, chunk_count=0),
            message="Parsing and indexing in progress",
        )
    try:
        extracted_title, content = await asyncio.to_thread(knowledge_service.extract_uploaded_content,
            filename=filename,
            content_type=file.content_type,
            data=raw_data,
        )
    except (ValueError, RuntimeError) as exc:
        raise ValidationException(str(exc)) from exc
    content_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
    existing = await db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.agent_id == agent_id,
            KnowledgeDocument.team_id == uuid.UUID(auth.team_id),
            KnowledgeDocument.source_filename == filename,
            KnowledgeDocument.source_hash == content_hash,
        ).order_by(KnowledgeDocument.created_at.desc()).limit(1)
    )
    if existing is not None:
        return BaseResponse.success(
            data=knowledge_service._read_model(existing, chunk_count=existing.chunk_count),
            message="Document already uploaded",
        )
    document = await knowledge_service.create_document(
        db,
        agent_id=agent_id,
        team_id=uuid.UUID(auth.team_id),
        title=(title or "").strip() or extracted_title,
        content=content,
        source_filename=filename,
        source_mime_type=file.content_type,
        indexing=True,
    )
    if document.chunk_count > BACKGROUND_INDEX_CHUNK_THRESHOLD:
        ACTIVE_INDEX_JOBS.add(document.id)
        background_tasks.add_task(_index_in_background, document.id, agent_id)
        return BaseResponse.success(data=document, message="Indexing in progress")
    ingestion = await knowledge_ingestion_service.ingest_document(
        db,
        document_id=document.id,
        agent_id=agent_id,
    )
    document.embedding_status = ingestion.status
    document.status = "ACTIVE" if ingestion.status == "completed" else "FAILED"
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
    team_id = uuid.UUID(auth.team_id)
    agent = await AgentService.get_agent_raw(db, agent_id)
    results, vector_error = await rag_retrieval_service.hybrid_search(
        db, agent_id=agent_id, team_id=team_id,
        agent_config=agent.config if agent else {}, query=payload.query,
        limit=payload.limit, retrieval_mode=payload.retrieval_mode,
        article_no=payload.article_no, include_near_misses=payload.include_near_misses,
        document_type=payload.document_type,
    )
    if vector_error:
        logger.warning("Knowledge test vector search failed: {}", vector_error)
    return BaseResponse.success(data=results, message="OK")


@router.post("/{document_id}/retry-index", response_model=BaseResponse[KnowledgeDocumentRead])
async def retry_knowledge_index(
    agent_id: uuid.UUID,
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth: AuthContext = Depends(get_current_user),
):
    await _ensure_agent_access(db, auth, agent_id)
    document = await db.get(KnowledgeDocument, document_id)
    if document is None or document.agent_id != agent_id or document.team_id != uuid.UUID(auth.team_id):
        raise NotFoundException(f"Knowledge document with ID {document_id} not found")
    stale_processing = (
        document.embedding_status == "processing"
        and document_id not in ACTIVE_INDEX_JOBS
        and document.updated_at is not None
        and (datetime.now(timezone.utc) - (
            document.updated_at.replace(tzinfo=timezone.utc)
            if document.updated_at.tzinfo is None else document.updated_at
        )) > timedelta(minutes=30)
    )
    if document.embedding_status != "failed" and not stale_processing:
        raise ValidationException("Only failed or inactive indexing jobs can be retried")
    if document.chunk_count == 0 and (document.document_metadata or {}).get("upload_job_version") == 1:
        if not (STAGED_UPLOAD_DIR / f"{document_id}.bin").is_file():
            raise ValidationException("Original staged file is unavailable for retry")
        document.status = "PROCESSING"
        document.embedding_status = "processing"
        document.embedding_error = None
        await db.commit()
        ACTIVE_INDEX_JOBS.add(document_id)
        background_tasks.add_task(_process_staged_upload, document_id, agent_id)
        await db.refresh(document)
        return BaseResponse.success(
            data=knowledge_service._read_model(document, chunk_count=0),
            message="Parsing and indexing in progress",
        )
    if document.chunk_count > BACKGROUND_INDEX_CHUNK_THRESHOLD:
        document.status = "PROCESSING"
        document.embedding_status = "processing"
        document.embedding_error = None
        await db.commit()
        ACTIVE_INDEX_JOBS.add(document_id)
        background_tasks.add_task(_index_in_background, document_id, agent_id)
        await db.refresh(document)
        return BaseResponse.success(
            data=knowledge_service._read_model(document, chunk_count=document.chunk_count),
            message="Indexing in progress",
        )
    result = await knowledge_ingestion_service.ingest_document(
        db, document_id=document_id, agent_id=agent_id,
    )
    await db.refresh(document)
    return BaseResponse.success(
        data=knowledge_service._read_model(document, chunk_count=document.chunk_count),
        message="Indexing completed" if result.status == "completed" else "Indexing failed",
    )


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
