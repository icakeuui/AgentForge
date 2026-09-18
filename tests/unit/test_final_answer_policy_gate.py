from backend.models.schemas import IntentClassificationResult
from backend.services.policy_gate import policy_gate


def _kb_required() -> IntentClassificationResult:
    return IntentClassificationResult(
        intent_type="KB_REQUIRED",
        query_subtype="exact_clause",
        confidence=0.92,
        requires_citation=True,
        allow_direct_answer=False,
    )


def _direct_chat() -> IntentClassificationResult:
    return IntentClassificationResult(
        intent_type="DIRECT_CHAT",
        query_subtype="smalltalk",
        confidence=0.8,
    )


def test_kb_required_miss_replaces_model_answer():
    decision = policy_gate.evaluate_final_answer(
        final_answer="第十条大概是禁止旷课。",
        classification=_kb_required(),
        retrieval_result={
            "matched": False,
            "knowledge_miss_answer": "当前知识库未检索到与「校规第十条是」直接匹配的内容。",
        },
        tool_call_history=[],
    )

    assert decision.accepted is False
    assert decision.violation_code == "ANSWER_WITHOUT_KB_MATCH"
    assert "当前知识库未检索到" in (decision.safe_final_answer or "")


def test_required_citation_is_appended_when_missing():
    decision = policy_gate.evaluate_final_answer(
        final_answer="第十条规定学生不得无故旷课。",
        classification=_kb_required(),
        retrieval_result={
            "matched": True,
            "knowledge_hits": [{"citation_label": "学生管理规定 / 第十条"}],
        },
        tool_call_history=[],
    )

    assert decision.accepted is False
    assert decision.violation_code == "MISSING_REQUIRED_CITATION"
    assert "学生管理规定 / 第十条" in (decision.safe_final_answer or "")


def test_unsupported_tool_result_claim_is_replaced():
    decision = policy_gate.evaluate_final_answer(
        final_answer="我已查询系统并提交了申请。",
        classification=_direct_chat(),
        retrieval_result={"matched": False},
        tool_call_history=[],
    )

    assert decision.accepted is False
    assert decision.violation_code == "UNSUPPORTED_TOOL_RESULT_CLAIM"
    assert "没有实际调用外部工具" in (decision.safe_final_answer or "")


def test_tool_result_claim_allowed_when_tool_was_called():
    decision = policy_gate.evaluate_final_answer(
        final_answer="我已查询系统，结果如下。",
        classification=_direct_chat(),
        retrieval_result={"matched": False},
        tool_call_history=["web_search"],
    )

    assert decision.accepted is True


def test_reasoning_and_pseudo_tool_call_text_are_sanitized():
    decision = policy_gate.evaluate_final_answer(
        final_answer="<think>private reasoning</think>\n我需要搜索。\n[TOOL_CALL]\n<tool_code>web_pages</tool_code><arg>{}</arg>",
        classification=_direct_chat(),
        retrieval_result={"matched": False},
        tool_call_history=[],
    )

    assert decision.accepted is False
    assert decision.violation_code == "FINAL_ANSWER_SANITIZED"
    assert "private reasoning" not in (decision.safe_final_answer or "")
    assert "TOOL_CALL" not in (decision.safe_final_answer or "")
