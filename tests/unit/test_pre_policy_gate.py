from backend.models.schemas import IntentClassificationResult
from backend.services.policy_gate import policy_gate
from backend.services.retrieval_policy_service import retrieval_policy_service


def _classification(intent_type: str, **updates):
    base = {
        "intent_type": intent_type,
        "query_subtype": "smalltalk",
        "confidence": 0.9,
        "matched_rules": [],
        "requires_citation": False,
        "allow_direct_answer": True,
        "requires_user_confirmation": False,
    }
    base.update(updates)
    return IntentClassificationResult(**base)


def test_direct_chat_keeps_model_driven_tool_candidates_available():
    classification = _classification("DIRECT_CHAT")
    retrieval_policy = retrieval_policy_service.resolve(classification)
    decision = policy_gate.evaluate_pre_policy(
        classification=classification,
        retrieval_policy=retrieval_policy,
        bound_tool_ids=["builtin/websearch", "builtin/python_exec"],
    )

    assert decision.retrieval_required is False
    assert decision.retrieval_mode == "none"
    assert decision.allowed_tool_ids_for_turn == ["builtin/websearch", "builtin/python_exec"]


def test_kb_required_enforces_required_retrieval():
    classification = _classification(
        "KB_REQUIRED",
        query_subtype="exact_clause",
        requires_citation=True,
        allow_direct_answer=False,
    )
    retrieval_policy = retrieval_policy_service.resolve(classification)
    decision = policy_gate.evaluate_pre_policy(
        classification=classification,
        retrieval_policy=retrieval_policy,
        bound_tool_ids=["builtin/websearch"],
    )

    assert decision.retrieval_required is True
    assert decision.retrieval_mode == "exact_clause"
    assert decision.requires_citation is True
    assert decision.allowed_tool_ids_for_turn == ["builtin/websearch"]


def test_tool_required_exposes_bound_tools_for_model_driven_selection():
    classification = _classification(
        "TOOL_REQUIRED",
        query_subtype="tool_operation",
        candidate_tool_domains=["web_search"],
        allow_direct_answer=False,
    )
    retrieval_policy = retrieval_policy_service.resolve(classification)
    decision = policy_gate.evaluate_pre_policy(
        classification=classification,
        retrieval_policy=retrieval_policy,
        bound_tool_ids=["builtin/websearch", "builtin/python_exec"],
        tool_catalog_entries=[
            {
                "id": "builtin/websearch",
                "risk_level": "medium",
                "side_effect": "external_read",
                "requires_confirmation": False,
                "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
                "domains": ["web_search"],
            },
            {
                "id": "builtin/python_exec",
                "risk_level": "high",
                "side_effect": "write",
                "requires_confirmation": True,
                "allowed_intents": ["TOOL_REQUIRED"],
                "domains": ["python"],
            },
        ],
    )

    assert decision.allowed_tool_ids_for_turn == ["builtin/websearch", "builtin/python_exec"]
    assert decision.blocked_tool_ids == []


def test_high_risk_confirmation_is_deferred_to_tool_call_policy():
    classification = _classification(
        "HIGH_RISK_TOOL",
        query_subtype="tool_operation",
        requires_user_confirmation=True,
        allow_direct_answer=False,
    )
    retrieval_policy = retrieval_policy_service.resolve(classification)
    decision = policy_gate.evaluate_pre_policy(
        classification=classification,
        retrieval_policy=retrieval_policy,
        bound_tool_ids=["builtin/python_exec"],
    )

    assert decision.requires_user_confirmation is False
    assert decision.allowed_tool_ids_for_turn == ["builtin/python_exec"]


def test_high_risk_pre_policy_exposes_bound_tools_before_argument_gate():
    classification = _classification(
        "HIGH_RISK_TOOL",
        query_subtype="tool_operation",
        requires_user_confirmation=True,
        allow_direct_answer=False,
    )
    retrieval_policy = retrieval_policy_service.resolve(classification)
    decision = policy_gate.evaluate_pre_policy(
        classification=classification,
        retrieval_policy=retrieval_policy,
        bound_tool_ids=["builtin/python_exec", "builtin/websearch"],
        tool_catalog_entries=[
            {
                "id": "builtin/python_exec",
                "risk_level": "high",
                "side_effect": "write",
                "requires_confirmation": True,
                "allowed_intents": ["TOOL_REQUIRED"],
                "domains": ["python"],
            },
            {
                "id": "builtin/websearch",
                "risk_level": "medium",
                "side_effect": "external_read",
                "requires_confirmation": False,
                "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
                "domains": ["web_search"],
            },
        ],
        confirmed_tool_actions=[
            {
                "tool_id": "builtin/python_exec",
                "arguments_hash": policy_gate.arguments_hash({"code": "print('ok')"}),
                "confirmed_at": "2026-04-27T00:00:00Z",
            }
        ],
    )

    assert decision.requires_user_confirmation is False
    assert decision.allowed_tool_ids_for_turn == ["builtin/python_exec", "builtin/websearch"]
