from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from backend.models.schemas import IntentClassificationResult
from backend.services.policy_gate import policy_gate
from backend.services.retrieval_policy_service import retrieval_policy_service
from backend.services.tool_need_classifier import tool_need_classifier

CASES_PATH = Path(__file__).with_name("policy_cases.yaml")

TOOL_CATALOG: dict[str, dict[str, Any]] = {
    "builtin/websearch": {
        "id": "builtin/websearch",
        "risk_level": "medium",
        "side_effect": "external_read",
        "requires_confirmation": False,
        "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
        "domains": ["web_search"],
        "max_calls_per_run": 2,
    },
    "builtin/python_exec": {
        "id": "builtin/python_exec",
        "risk_level": "high",
        "side_effect": "write",
        "requires_confirmation": True,
        "allowed_intents": ["TOOL_REQUIRED"],
        "domains": ["python"],
        "max_calls_per_run": 1,
    },
}


def _load_cases() -> list[dict[str, Any]]:
    with CASES_PATH.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or []
    assert isinstance(loaded, list)
    return loaded


def _inspect_policy(case: dict[str, Any]):
    bound_tools = list(case.get("bound_tools") or [])
    tool_catalog_entries = [TOOL_CATALOG[tool_id] for tool_id in bound_tools if tool_id in TOOL_CATALOG]
    classification = tool_need_classifier.classify(
        str(case["input"]),
        tool_catalog_summary=list(TOOL_CATALOG.keys()),
    )
    retrieval_policy = retrieval_policy_service.resolve(classification)
    pre_policy = policy_gate.evaluate_pre_policy(
        classification=classification,
        retrieval_policy=retrieval_policy,
        bound_tool_ids=bound_tools,
        tool_catalog_entries=tool_catalog_entries,
        confirmed_tool_actions=[],
    )
    return classification, retrieval_policy, pre_policy


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["case_id"])
def test_policy_eval_cases(case: dict[str, Any]):
    classification, retrieval_policy, pre_policy = _inspect_policy(case)

    assert classification.intent_type == case["expected_intent_type"]
    assert classification.query_subtype == case["expected_query_subtype"]
    assert retrieval_policy.required is case["expected_retrieval_required"]
    assert pre_policy.allowed_tool_ids_for_turn == case["expected_tool_allowed"]
    blocked_ids = [item.tool_id for item in pre_policy.blocked_tool_ids]
    assert blocked_ids == case["expected_tool_blocked"]

    expected_behavior = case["expected_final_behavior"]
    if expected_behavior == "knowledge_miss":
        assert classification.intent_type == "KB_REQUIRED"
        assert retrieval_policy.required is True
        assert case.get("knowledge_fixture") is None
    elif expected_behavior == "tool_call_policy_confirmation":
        assert classification.requires_user_confirmation is True
        assert pre_policy.requires_user_confirmation is False
    elif expected_behavior == "clarify":
        assert classification.intent_type in {"TOOL_REQUIRED", "CLARIFY_REQUIRED"}
        assert pre_policy.direct_answer_allowed is False
    elif expected_behavior == "answer":
        assert pre_policy.requires_user_confirmation is False
    else:
        raise AssertionError(f"Unknown expected_final_behavior: {expected_behavior}")


def test_policy_eval_metrics():
    cases = _load_cases()
    inspected = [(case, *_inspect_policy(case)) for case in cases]

    kb_required_cases = [item for item in inspected if item[0]["expected_retrieval_required"]]
    kb_required_recall = sum(1 for _case, _classification, retrieval_policy, _pre_policy in kb_required_cases if retrieval_policy.required) / len(kb_required_cases)

    direct_chat_cases = [item for item in inspected if item[0]["expected_intent_type"] == "DIRECT_CHAT" and item[0].get("bound_tools")]
    direct_chat_tool_candidate_rate = sum(1 for _case, _classification, _retrieval_policy, pre_policy in direct_chat_cases if pre_policy.allowed_tool_ids_for_turn) / max(len(direct_chat_cases), 1)

    classification_log_coverage = sum(1 for _case, classification, _retrieval_policy, _pre_policy in inspected if isinstance(classification, IntentClassificationResult)) / len(inspected)
    tool_policy_log_coverage = sum(1 for _case, _classification, _retrieval_policy, pre_policy in inspected if pre_policy is not None) / len(inspected)

    assert kb_required_recall >= 0.98
    assert direct_chat_tool_candidate_rate == 1.0
    assert classification_log_coverage == 1.0
    assert tool_policy_log_coverage == 1.0
