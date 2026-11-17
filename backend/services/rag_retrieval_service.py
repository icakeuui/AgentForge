from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.orm import KnowledgeChunk, KnowledgeDocument
from backend.models.schemas import KnowledgeSearchResult
from backend.services.knowledge_service import knowledge_service
from backend.services.embedding.factory import create_embedding_provider
from backend.services.vector_store.qdrant_store import QdrantVectorStore


class RAGRetrievalService:
    async def hybrid_search(
        self,
        db: AsyncSession,
        *,
        agent_id: uuid.UUID,
        team_id: uuid.UUID,
        agent_config: dict[str, Any],
        query: str,
        limit: int = 5,
        retrieval_mode: str = "optional_hybrid",
        article_no: str | None = None,
        include_near_misses: bool = True,
        document_type: str | None = None,
        max_chunks_per_document: int | None = None,
    ) -> tuple[list[KnowledgeSearchResult], str | None]:
        """Combine independently authorized vector and keyword evidence.

        Rank fusion uses each retriever's ordering rather than comparing their
        incompatible raw scores. Failed vector queries still permit text search.
        """
        candidate_limit = min(max(limit * 4, limit), 40)
        keyword = await knowledge_service.search(
            db, agent_id=agent_id, team_id=team_id, query=query,
            limit=candidate_limit, retrieval_mode=retrieval_mode,
            article_no=article_no, include_near_misses=include_near_misses,
            document_type=document_type,
            max_chunks_per_document=max_chunks_per_document,
        )
        if retrieval_mode not in {"optional_hybrid", "required_hybrid"} or document_type:
            selected = keyword[:limit]
            if self.needs_adjacent_expansion(query):
                selected = await self.expand_adjacent_chunks(
                    db, hits=selected, agent_id=agent_id, team_id=team_id,
                    max_results=min(40, max(limit, limit * 2)),
                )
            return selected, None

        indexed_document = await db.scalar(
            select(KnowledgeDocument.id).where(
                KnowledgeDocument.agent_id == agent_id,
                KnowledgeDocument.team_id == team_id,
                KnowledgeDocument.status == "ACTIVE",
                KnowledgeDocument.embedding_status == "completed",
            ).limit(1)
        )
        if indexed_document is None:
            return keyword[:limit], None

        vector: list[KnowledgeSearchResult] = []
        vector_error = None
        try:
            vector = await self.vector_search(
                db, agent_id=agent_id, team_id=team_id,
                agent_config=agent_config, query=query, limit=candidate_limit,
                max_chunks_per_document=max_chunks_per_document,
            )
        except Exception as exc:
            vector_error = f"{type(exc).__name__}: {exc}"

        fused: dict[uuid.UUID, tuple[KnowledgeSearchResult, float, set[str]]] = {}
        for source, hits, weight in (("keyword", keyword, 1.2), ("vector", vector, 1.0)):
            for rank, hit in enumerate(hits, start=1):
                # A lone weak vector match is insufficient evidence. A keyword
                # match may still qualify independently of vector similarity.
                if source == "vector" and hit.score < 0.5 and hit.chunk_id not in fused:
                    continue
                previous = fused.get(hit.chunk_id)
                score = weight / (60 + rank) + (previous[1] if previous else 0.0)
                sources = (previous[2] if previous else set()) | {source}
                preferred = hit if source == "keyword" or previous is None else previous[0]
                fused[hit.chunk_id] = (preferred, score, sources)

        ordered = sorted(fused.values(), key=lambda item: item[1], reverse=True)
        selected: list[KnowledgeSearchResult] = []
        per_document: dict[uuid.UUID, int] = {}
        for hit, score, sources in ordered:
            if max_chunks_per_document is not None and per_document.get(hit.document_id, 0) >= max_chunks_per_document:
                continue
            selected.append(hit.model_copy(update={
                "score": score,
                "match_type": "hybrid" if len(sources) == 2 else hit.match_type,
            }))
            per_document[hit.document_id] = per_document.get(hit.document_id, 0) + 1
            if len(selected) >= limit:
                break
        if self.needs_adjacent_expansion(query):
            selected = await self.expand_adjacent_chunks(
                db, hits=selected, agent_id=agent_id, team_id=team_id,
                max_results=min(40, max(limit, limit * 2)),
            )
        return selected, vector_error

    @staticmethod
    def needs_adjacent_expansion(query: str) -> bool:
        normalized = "".join((query or "").lower().split())
        markers = (
            "完整", "全部", "所有", "逐条", "逐项", "列表", "表格", "目录", "章节",
            "主要特点", "四个目标", "六个", "十三", "13", "跨章节", "跨文件", "综合分析",
        )
        return any(marker in normalized for marker in markers)

    async def expand_adjacent_chunks(
        self,
        db: AsyncSession,
        *,
        hits: list[KnowledgeSearchResult],
        agent_id: uuid.UUID,
        team_id: uuid.UUID,
        max_results: int = 40,
    ) -> list[KnowledgeSearchResult]:
        """Add immediate neighbors while repeating the full ownership filter in SQL."""
        if not hits or max_results <= len(hits):
            return hits[:max_results]

        hit_ids = [hit.chunk_id for hit in hits]
        anchor_rows = await db.execute(
            select(KnowledgeChunk.id, KnowledgeChunk.document_id, KnowledgeChunk.chunk_index).where(
                KnowledgeChunk.id.in_(hit_ids),
                KnowledgeChunk.agent_id == agent_id,
                KnowledgeChunk.team_id == team_id,
            )
        )
        anchors = {chunk_id: (document_id, chunk_index) for chunk_id, document_id, chunk_index in anchor_rows.all()}
        requested_by_document: dict[uuid.UUID, set[int]] = {}
        for hit in hits:
            anchor = anchors.get(hit.chunk_id)
            if anchor is None:
                continue
            document_id, chunk_index = anchor
            requested_by_document.setdefault(document_id, set()).update(
                index for index in (chunk_index - 1, chunk_index + 1) if index >= 0
            )
        if not requested_by_document:
            return hits[:max_results]

        neighbor_scope = or_(*[
            and_(KnowledgeChunk.document_id == document_id, KnowledgeChunk.chunk_index.in_(sorted(indices)))
            for document_id, indices in requested_by_document.items()
        ])
        rows = await db.execute(
            select(
                KnowledgeChunk,
                KnowledgeDocument.document_type,
                KnowledgeDocument.title,
                KnowledgeDocument.source_filename,
            )
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(
                neighbor_scope,
                KnowledgeChunk.agent_id == agent_id,
                KnowledgeChunk.team_id == team_id,
                KnowledgeDocument.agent_id == agent_id,
                KnowledgeDocument.team_id == team_id,
                KnowledgeDocument.status == "ACTIVE",
                KnowledgeDocument.embedding_status == "completed",
            )
        )
        neighbor_rows = {
            (chunk.document_id, chunk.chunk_index): (chunk, document_type or "other", document_title, source_filename)
            for chunk, document_type, document_title, source_filename in rows.all()
        }

        expanded: list[KnowledgeSearchResult] = []
        seen: set[uuid.UUID] = set()
        for hit in hits:
            anchor = anchors.get(hit.chunk_id)
            if anchor is None:
                candidates: list[KnowledgeSearchResult] = [hit]
            else:
                document_id, chunk_index = anchor
                candidates = []
                for neighbor_index in (chunk_index - 1, chunk_index):
                    if neighbor_index == chunk_index:
                        candidates.append(hit)
                        continue
                    row = neighbor_rows.get((document_id, neighbor_index))
                    if row is not None:
                        candidates.append(self._neighbor_result(row, anchor_hit=hit))
                row = neighbor_rows.get((document_id, chunk_index + 1))
                if row is not None:
                    candidates.append(self._neighbor_result(row, anchor_hit=hit))
            for candidate in candidates:
                if candidate.chunk_id in seen:
                    continue
                seen.add(candidate.chunk_id)
                expanded.append(candidate)
                if len(expanded) >= max_results:
                    return expanded
        return expanded

    @staticmethod
    def _neighbor_result(
        row: tuple[KnowledgeChunk, str, str | None, str | None],
        *,
        anchor_hit: KnowledgeSearchResult,
    ) -> KnowledgeSearchResult:
        chunk, document_type, document_title, source_filename = row
        return KnowledgeSearchResult(
            document_id=chunk.document_id,
            chunk_id=chunk.id,
            title=chunk.title,
            document_title=document_title,
            source_filename=source_filename,
            content=chunk.content,
            score=max(0.0, float(anchor_hit.score) * 0.98),
            match_type="adjacent",
            document_type=document_type,
            article_no=chunk.article_no,
            article_label=chunk.article_label,
            section_path=chunk.section_path or [chunk.title, f"片段 {chunk.chunk_index + 1}"],
            page_no=chunk.page_no,
            citation_label=f"{chunk.title} / {chunk.article_label or f'片段 {chunk.chunk_index + 1}'}",
            is_direct_evidence=True,
        )

    async def vector_search(
        self,
        db: AsyncSession,
        *,
        agent_id: uuid.UUID,
        team_id: uuid.UUID,
        agent_config: dict[str, Any],
        query: str,
        limit: int = 5,
        max_chunks_per_document: int | None = None,
    ) -> list[KnowledgeSearchResult]:
        embedding_config = agent_config.get("embedding") if isinstance(agent_config, dict) else None
        if not isinstance(embedding_config, dict):
            raise ValueError("Embedding configuration is missing")

        provider = create_embedding_provider(embedding_config)
        query_vector = await provider.embed_query(query)
        if not query_vector:
            raise ValueError("Embedding provider returned an empty query vector")

        vector_store = QdrantVectorStore()
        candidate_limit = min(max(limit * 4, limit), 40) if max_chunks_per_document is not None else limit
        matches = await vector_store.search(
            query_vector,
            agent_id=str(agent_id),
            model=provider.model_name,
            limit=candidate_limit,
        )
        if not matches:
            return []

        scored_chunks: list[tuple[KnowledgeChunk, str, str | None, str | None, float]] = []
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
            select(
                KnowledgeChunk,
                KnowledgeDocument.document_type,
                KnowledgeDocument.title,
                KnowledgeDocument.source_filename,
            )
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(
                KnowledgeChunk.id.in_(chunk_ids),
                KnowledgeChunk.agent_id == agent_id,
                KnowledgeChunk.team_id == team_id,
                KnowledgeDocument.agent_id == agent_id,
                KnowledgeDocument.team_id == team_id,
                KnowledgeDocument.status == "ACTIVE",
                KnowledgeDocument.embedding_status == "completed",
                KnowledgeChunk.embedding_status == "completed",
            )
        )
        chunk_rows = {
            chunk.id: (chunk, document_type or "other", document_title, source_filename)
            for chunk, document_type, document_title, source_filename in rows.all()
        }
        for chunk_id in chunk_ids:
            row = chunk_rows.get(chunk_id)
            if row is not None:
                scored_chunks.append((row[0], row[1], row[2], row[3], score_by_id[chunk_id]))

        scored_chunks.sort(key=lambda item: item[4], reverse=True)
        results: list[KnowledgeSearchResult] = []
        per_document: dict[uuid.UUID, int] = {}
        for chunk, document_type, document_title, source_filename, score in scored_chunks:
            if max_chunks_per_document is not None and per_document.get(chunk.document_id, 0) >= max_chunks_per_document:
                continue
            results.append(KnowledgeSearchResult(
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                title=chunk.title,
                document_title=document_title,
                source_filename=source_filename,
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
            ))
            per_document[chunk.document_id] = per_document.get(chunk.document_id, 0) + 1
            if len(results) >= limit:
                break
        return results


rag_retrieval_service = RAGRetrievalService()
