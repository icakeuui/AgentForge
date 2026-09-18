import uuid

from backend.models.orm import KnowledgeChunk
from backend.services.knowledge_retrieval_ranker import knowledge_retrieval_ranker
from backend.services.knowledge_service import knowledge_service


TEST_TEAM_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _chunk(
    *,
    content: str,
    token_text: str,
    article_no: str | None = None,
    title: str = "学生管理规定",
) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        team_id=TEST_TEAM_ID,
        title=title,
        content=content,
        chunk_index=0,
        token_text=token_text,
        chunk_type="article" if article_no else "plain",
        section_path=[title],
        article_no=article_no,
        article_label=f"第{article_no}条" if article_no else None,
        page_no=None,
        start_char=0,
        end_char=len(content),
        chunk_metadata={},
    )


def test_exact_clause_matches_article_before_keyword_scoring():
    chunks = [
        _chunk(content="第九条 学生应按时上课。", token_text="学生 按时 上课", article_no="9"),
        _chunk(content="第十条 学生不得无故旷课。", token_text="学生 不得 无故旷课", article_no="10"),
    ]

    ranked = knowledge_retrieval_ranker.rank(
        chunks=chunks,
        query="校规第十条是",
        query_tokens=knowledge_service._filter_query_tokens(knowledge_service._tokenize("校规第十条是")),
        retrieval_mode="exact_clause",
        requested_article_no="10",
        include_near_misses=True,
        extract_article_no=knowledge_service.extract_article_no,
        token_weight=knowledge_service._token_weight,
    )

    assert [item.chunk.article_no for item in ranked] == ["10"]
    assert ranked[0].score == 100.0
    assert ranked[0].match_type == "exact_clause"
    assert ranked[0].is_direct_evidence is True


def test_exact_clause_can_return_empty_when_near_misses_disabled():
    chunks = [_chunk(content="第十条 学生不得无故旷课。", token_text="学生 不得 无故旷课", article_no="10")]

    ranked = knowledge_retrieval_ranker.rank(
        chunks=chunks,
        query="校规第十一条是",
        query_tokens=knowledge_service._filter_query_tokens(knowledge_service._tokenize("校规第十一条是")),
        retrieval_mode="exact_clause",
        requested_article_no="11",
        include_near_misses=False,
        extract_article_no=knowledge_service.extract_article_no,
        token_weight=knowledge_service._token_weight,
    )

    assert ranked == []


def test_keyword_ranking_orders_by_weighted_overlap():
    lower = _chunk(content="校园活动通知", token_text="校园 活动 通知")
    higher = _chunk(content="学生旷课处分规定", token_text="学生 旷课 处分 规定")

    ranked = knowledge_retrieval_ranker.rank(
        chunks=[lower, higher],
        query="学生旷课处分",
        query_tokens=knowledge_service._filter_query_tokens(knowledge_service._tokenize("学生旷课处分")),
        retrieval_mode="required_hybrid",
        requested_article_no=None,
        include_near_misses=True,
        extract_article_no=knowledge_service.extract_article_no,
        token_weight=knowledge_service._token_weight,
    )

    assert ranked
    assert ranked[0].chunk.content == "学生旷课处分规定"
    assert ranked[0].match_type == "keyword"
    assert ranked[0].is_direct_evidence is True
