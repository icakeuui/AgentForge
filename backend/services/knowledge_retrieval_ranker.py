from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from backend.models.orm import KnowledgeChunk


@dataclass(slots=True)
class RankedKnowledgeChunk:
    chunk: KnowledgeChunk
    score: float
    match_type: str
    is_direct_evidence: bool


class KnowledgeRetrievalRanker:
    """Rule-first ranking for knowledge retrieval.

    Phase 3 intentionally keeps this deterministic: exact article matches beat
    keyword overlap, and exact-clause fallback candidates are marked as near misses.
    """

    SEARCH_MIN_SCORE = 2.0
    SEARCH_MIN_UNIQUE_OVERLAP = 2
    SEARCH_MIN_SINGLE_OVERLAP_SCORE = 2.0

    def rank(
        self,
        *,
        chunks: Sequence[KnowledgeChunk],
        query: str,
        query_tokens: Iterable[str],
        retrieval_mode: str,
        requested_article_no: str | None,
        include_near_misses: bool,
        extract_article_no: Callable[[str], str | None],
        token_weight: Callable[[str], float],
    ) -> list[RankedKnowledgeChunk]:
        if retrieval_mode == "exact_clause" and requested_article_no:
            exact_matches = self._exact_clause_matches(
                chunks=chunks,
                requested_article_no=requested_article_no,
                extract_article_no=extract_article_no,
            )
            if exact_matches:
                return exact_matches
            if not include_near_misses:
                return []

        return self._keyword_matches(
            chunks=chunks,
            query=query,
            query_tokens=list(query_tokens),
            retrieval_mode=retrieval_mode,
            token_weight=token_weight,
        )

    @staticmethod
    def _exact_clause_matches(
        *,
        chunks: Sequence[KnowledgeChunk],
        requested_article_no: str,
        extract_article_no: Callable[[str], str | None],
    ) -> list[RankedKnowledgeChunk]:
        ranked: list[RankedKnowledgeChunk] = []
        for chunk in chunks:
            chunk_article_no = chunk.article_no or extract_article_no(chunk.content)
            if chunk_article_no != requested_article_no:
                continue
            ranked.append(
                RankedKnowledgeChunk(
                    chunk=chunk,
                    score=100.0,
                    match_type="exact_clause",
                    is_direct_evidence=True,
                )
            )
        return ranked

    @classmethod
    def _keyword_matches(
        cls,
        *,
        chunks: Sequence[KnowledgeChunk],
        query: str,
        query_tokens: list[str],
        retrieval_mode: str,
        token_weight: Callable[[str], float],
    ) -> list[RankedKnowledgeChunk]:
        normalized_query = query.strip().lower()
        query_counter = Counter(query_tokens)
        ranked: list[RankedKnowledgeChunk] = []
        for chunk in chunks:
            chunk_counter = Counter((chunk.token_text or "").split())
            weighted_overlap = sum(
                min(count, chunk_counter.get(token, 0)) * token_weight(token)
                for token, count in query_counter.items()
            )
            unique_overlap = sum(1 for token in query_counter if chunk_counter.get(token, 0) > 0)
            phrase_bonus = cls._phrase_bonus(normalized_query, chunk)
            score = float(weighted_overlap + phrase_bonus)
            min_score = cls.SEARCH_MIN_SCORE
            if phrase_bonus == 0 and unique_overlap < cls.SEARCH_MIN_UNIQUE_OVERLAP:
                min_score = cls.SEARCH_MIN_SINGLE_OVERLAP_SCORE
            if score < min_score:
                continue
            ranked.append(
                RankedKnowledgeChunk(
                    chunk=chunk,
                    score=score,
                    match_type="keyword",
                    is_direct_evidence=score >= cls.SEARCH_MIN_SCORE and retrieval_mode != "exact_clause",
                )
            )
        return sorted(ranked, key=lambda item: item.score, reverse=True)

    @staticmethod
    def _phrase_bonus(normalized_query: str, chunk: KnowledgeChunk) -> float:
        if not normalized_query:
            return 0.0
        phrase_bonus = 0.0
        if normalized_query in (chunk.title or "").lower():
            phrase_bonus += 2.0
        if normalized_query in chunk.content.lower():
            phrase_bonus += 2.0
        return phrase_bonus


knowledge_retrieval_ranker = KnowledgeRetrievalRanker()
