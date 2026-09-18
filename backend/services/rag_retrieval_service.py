from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.orm import KnowledgeChunk, KnowledgeDocument
from backend.models.schemas import KnowledgeSearchResult
from backend.services.embedding.factory import create_embedding_provider
from backend.services.vector_store.qdrant_store import QdrantVectorStore


class RAGRetrievalService:
    async def vector_search(
        self,
        db: AsyncSession,
        *,
        agent_id: uuid.UUID,
        team_id: uuid.UUID,
        agent_config: dict[str, Any],
        query: str,
        limit: int = 5,
    ) -> list[KnowledgeSearchResult]:
        embedding_config = agent_config.get("embedding") if isinstance(agent_config, dict) else None
        if not isinstance(embedding_config, dict):
            raise ValueError("Embedding configuration is missing")

        provider = create_embedding_provider(embedding_config)
        query_vector = await provider.embed_query(query)
        if not query_vector:
            raise ValueError("Embedding provider returned an empty query vector")

        vector_store = QdrantVectorStore()
        matches = await vector_store.search(
            query_vector,
            agent_id=str(agent_id),
            limit=limit,
        )
        if not matches:
            return []

        scored_chunks: list[tuple[KnowledgeChunk, str, float]] = []
        chunk_ids: list[uuid.UUID] = []
        score_by_id: dict[uuid.UUID, float] = {}
        for match in matches:
            payload = match.get("payload") or {}
            raw_chunk_id = payload.get("chunk_id") or match.get("id")
            try:
                chunk_id = uuid.UUID(str(raw_chunk_id))
            except (ValueError, TypeError, AttributeError):
                continue
            chunk_ids.append(chunk_id)
            score_by_id[chunk_id] = float(match.get("score", 0.0))

        if not chunk_ids:
            return []

        rows = await db.execute(
            select(KnowledgeChunk, KnowledgeDocument.document_type)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(
                KnowledgeChunk.id.in_(chunk_ids),
                KnowledgeChunk.agent_id == agent_id,
                KnowledgeChunk.team_id == team_id,
                KnowledgeDocument.agent_id == agent_id,
                KnowledgeDocument.team_id == team_id,
            )
        )
        chunk_rows = {chunk.id: (chunk, document_type or "other") for chunk, document_type in rows.all()}
        for chunk_id in chunk_ids:
            row = chunk_rows.get(chunk_id)
            if row is not None:
                scored_chunks.append((row[0], row[1], score_by_id[chunk_id]))

        scored_chunks.sort(key=lambda item: item[2], reverse=True)
        return [
            KnowledgeSearchResult(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                title=chunk.title,
                content=chunk.content,
                score=score,
                match_type="vector",
                document_type=document_type,
                article_no=chunk.article_no,
                article_label=chunk.article_label,
                section_path=chunk.section_path or [chunk.title, chunk.article_label or f"片段 {chunk.chunk_index + 1}"],
                page_no=chunk.page_no,
                citation_label=f"{chunk.title} / {chunk.article_label or f'片段 {chunk.chunk_index + 1}'}",
                is_direct_evidence=False,
            )
            for chunk, document_type, score in scored_chunks[:limit]
        ]


rag_retrieval_service = RAGRetrievalService()
