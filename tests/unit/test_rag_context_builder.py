from types import SimpleNamespace
import uuid

from backend.services.langgraph_execution_strategy import LangGraphExecutionStrategy


def _hit(index: int, content: str):
    return SimpleNamespace(
        document_id=uuid.uuid4(), chunk_id=uuid.uuid4(), title=f"资料 {index}",
        document_title=f"资料 {index}", source_filename=f"资料 {index}.pdf",
        content=content, score=1.0, match_type="hybrid", document_type="pdf",
        article_no=None, article_label=None, section_path=[f"第 {index} 节"],
        page_no=index, citation_label=f"资料 {index} / 片段 {index}", is_direct_evidence=True,
    )


def test_context_builder_keeps_complete_chunks_within_token_budget():
    hits = [_hit(index, f"完整表格第 {index} 行：" + "内容" * 300) for index in range(1, 6)]
    metadata, context, original_chars, injected_chars, used_tokens, dropped = (
        LangGraphExecutionStrategy._build_knowledge_context_items(hits, token_budget=8000)
    )
    assert len(metadata) == 5
    assert not dropped
    assert all(not item["truncated"] for item in metadata)
    assert all(f"完整表格第 {index} 行" in context for index in range(1, 6))
    assert injected_chars >= original_chars
    assert used_tokens <= 8000


def test_context_builder_reports_budget_drops_instead_of_silent_truncation():
    hits = [_hit(index, "长内容" * 600) for index in range(1, 5)]
    metadata, _context, _original_chars, _injected_chars, used_tokens, dropped = (
        LangGraphExecutionStrategy._build_knowledge_context_items(hits, token_budget=900)
    )
    assert metadata
    assert dropped
    assert used_tokens <= 900
    assert all(item["reason"] in {"rag_token_budget_exhausted", "single_evidence_exceeds_rag_token_budget"} for item in dropped)
