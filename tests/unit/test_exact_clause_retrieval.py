import uuid

import pytest
from sqlalchemy import select

from backend.models.orm import KnowledgeChunk
from backend.services.knowledge_service import knowledge_service

TEST_TEAM_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_create_document_persists_article_metadata(db_session):
    agent_id = uuid.uuid4()
    document = await knowledge_service.create_document(
        db_session,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
        title="学生管理规定",
        content="第一章 总则\n第十条 学生不得无故旷课。\n第十一条 学生应按时参加考试。",
    )

    rows = await db_session.execute(
        select(KnowledgeChunk).where(KnowledgeChunk.agent_id == agent_id).order_by(KnowledgeChunk.chunk_index)
    )
    chunks = list(rows.scalars().all())
    assert document.metadata["article_count"] == 2
    assert [chunk.article_no for chunk in chunks] == ["10", "11"]
    assert chunks[0].chunk_type == "article"
    assert chunks[0].section_path == ["学生管理规定", "第一章", "第十条"]


@pytest.mark.asyncio
async def test_exact_clause_retrieval_uses_article_field_and_misses_absent_article(db_session):
    agent_id = uuid.uuid4()
    await knowledge_service.create_document(
        db_session,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
        title="学生管理规定",
        content="第十条 学生不得无故旷课。",
    )

    hit = await knowledge_service.search(
        db_session,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
        query="校规第10条是",
        retrieval_mode="exact_clause",
    )
    miss = await knowledge_service.search(
        db_session,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
        query="校规第十一条是",
        retrieval_mode="exact_clause",
        include_near_misses=False,
    )

    assert hit
    assert hit[0].article_no == "10"
    assert hit[0].match_type == "exact_clause"
    assert miss == []


@pytest.mark.asyncio
async def test_search_can_filter_by_document_type(db_session):
    agent_id = uuid.uuid4()
    await knowledge_service.create_document(
        db_session,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
        title="学生管理规定",
        content="第十条 学生不得无故旷课。",
    )

    school_rule_results = await knowledge_service.search(
        db_session,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
        query="第十条",
        retrieval_mode="exact_clause",
        document_type="school_rule",
    )
    contract_results = await knowledge_service.search(
        db_session,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
        query="第十条",
        retrieval_mode="exact_clause",
        document_type="contract",
    )

    assert school_rule_results
    assert school_rule_results[0].document_type == "school_rule"
    assert contract_results == []
