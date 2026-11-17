import uuid

import pytest

from backend.models.orm import KnowledgeChunk, KnowledgeDocument
from backend.models.schemas import KnowledgeSearchResult
from backend.services.rag_retrieval_service import rag_retrieval_service


@pytest.mark.asyncio
async def test_adjacent_expansion_repeats_agent_team_and_document_scope(db_session):
    agent_id, team_id = uuid.uuid4(), uuid.uuid4()
    other_agent_id, other_team_id = uuid.uuid4(), uuid.uuid4()
    document_id, other_document_id = uuid.uuid4(), uuid.uuid4()
    db_session.add_all([
        KnowledgeDocument(
            id=document_id, agent_id=agent_id, team_id=team_id, title="允许文档", content="正文",
            document_type="pdf", status="ACTIVE", embedding_status="completed", chunk_count=3,
        ),
        KnowledgeDocument(
            id=other_document_id, agent_id=other_agent_id, team_id=other_team_id, title="其他团队文档",
            content="私有正文", document_type="pdf", status="ACTIVE", embedding_status="completed", chunk_count=3,
        ),
    ])
    own_chunks = [
        KnowledgeChunk(
            document_id=document_id, agent_id=agent_id, team_id=team_id, title="允许文档",
            content=f"允许片段 {index}", chunk_index=index, token_text=f"允许 片段 {index}",
            embedding_status="completed",
        ) for index in range(3)
    ]
    other_chunks = [
        KnowledgeChunk(
            document_id=other_document_id, agent_id=other_agent_id, team_id=other_team_id, title="其他团队文档",
            content=f"私有片段 {index}", chunk_index=index, token_text=f"私有 片段 {index}",
            embedding_status="completed",
        ) for index in range(3)
    ]
    db_session.add_all([*own_chunks, *other_chunks])
    await db_session.commit()
    hit = KnowledgeSearchResult(
        document_id=document_id, chunk_id=own_chunks[1].id, title="允许文档", document_title="允许文档",
        source_filename="允许文档.pdf", content=own_chunks[1].content, score=1.0,
        match_type="hybrid", document_type="pdf", citation_label="允许文档 / 片段 2",
    )
    expanded = await rag_retrieval_service.expand_adjacent_chunks(
        db_session, hits=[hit], agent_id=agent_id, team_id=team_id, max_results=10,
    )
    assert [item.content for item in expanded] == ["允许片段 0", "允许片段 1", "允许片段 2"]
    assert all(item.document_id == document_id for item in expanded)
    assert not any("私有" in item.content for item in expanded)
