from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.orm import Agent, KnowledgeChunk, KnowledgeDocument
from backend.services.embedding.factory import create_embedding_provider
from backend.services.vector_store.qdrant_store import QdrantVectorStore


@dataclass
class IngestionResult:
    status: str
    embedded_chunk_count: int
    provider: str | None = None
    model: str | None = None
    dimensions: int | None = None
    error: str | None = None


class KnowledgeIngestionService:
    async def ingest_document(
        self,
        db: AsyncSession,
        *,
        document_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> IngestionResult:
        document = await db.get(KnowledgeDocument, document_id)
        agent = await db.get(Agent, agent_id)
        if document is None or agent is None:
            return IngestionResult(status="failed", embedded_chunk_count=0, error="Document or agent not found")

        chunks_result = await db.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id, KnowledgeChunk.agent_id == agent_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        chunks = list(chunks_result.scalars().all())
        config = agent.config if isinstance(agent.config, dict) else {}
        embedding_config = config.get("embedding") if isinstance(config.get("embedding"), dict) else {}
        document.embedding_status = "processing"
        document.status = "PROCESSING"
        document.embedding_error = None
        await db.commit()

        try:
            provider = create_embedding_provider(embedding_config)
            if not chunks:
                raise ValueError("Document has no searchable chunks")
            vector_store = QdrantVectorStore()
            dimensions = 0
            for offset in range(0, len(chunks), 32):
                batch = chunks[offset:offset + 32]
                vectors = await provider.embed_documents([f"{chunk.title}\n{chunk.content}" for chunk in batch])
                if len(vectors) != len(batch) or not vectors:
                    raise ValueError("Embedding provider returned an incomplete vector batch")
                batch_dimensions = len(vectors[0])
                if not batch_dimensions or any(len(vector) != batch_dimensions for vector in vectors):
                    raise ValueError("Embedding vectors have inconsistent dimensions")
                if dimensions and dimensions != batch_dimensions:
                    raise ValueError("Embedding dimensions changed between batches")
                dimensions = batch_dimensions
                await vector_store.upsert([
                    {
                        "id": str(chunk.id),
                        "vector": vector,
                        "payload": {
                            "agent_id": str(agent_id),
                            "team_id": str(document.team_id),
                            "document_id": str(document.id),
                            "chunk_id": str(chunk.id),
                            "model": provider.model_name,
                            "dimensions": dimensions,
                            "chunk_index": chunk.chunk_index,
                        },
                    }
                    for chunk, vector in zip(batch, vectors)
                ], dimensions)
        except Exception as exc:
            document.embedding_status = "failed"
            document.status = "FAILED"
            document.embedding_error = str(exc)[:2000]
            for chunk in chunks:
                chunk.embedding_status = "failed"
            await db.commit()
            return IngestionResult(status="failed", embedded_chunk_count=0, error=document.embedding_error)

        document.embedding_status = "completed"
        document.status = "ACTIVE"
        document.embedding_provider = embedding_config.get("provider", "openai_compatible")
        document.embedding_model_name = provider.model_name
        document.embedding_dimensions = dimensions
        document.embedding_error = None
        document.chunk_count = len(chunks)
        for chunk in chunks:
            chunk.embedding_status = "completed"
            chunk.embedding_model_name = provider.model_name
            chunk.embedding_dimensions = dimensions
            chunk.vector_point_id = str(chunk.id)
        await db.commit()
        return IngestionResult(
            status="completed",
            embedded_chunk_count=len(chunks),
            provider=document.embedding_provider,
            model=provider.model_name,
            dimensions=dimensions,
        )


knowledge_ingestion_service = KnowledgeIngestionService()
