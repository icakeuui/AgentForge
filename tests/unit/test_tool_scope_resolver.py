from backend.models.schemas import IntentClassificationResult
from backend.services.tool_scope_resolver import tool_scope_resolver


def _schema(tool_id: str) -> dict:
    return {"type": "function", "function": {"name": tool_id, "parameters": {"type": "object"}}}


def _classification(intent_type: str, **updates) -> IntentClassificationResult:
    payload = {
        "intent_type": intent_type,
        "query_subtype": "tool_operation",
        "confidence": 0.9,
        "candidate_tool_domains": [],
        "allow_direct_answer": False,
    }
    payload.update(updates)
    return IntentClassificationResult(**payload)


def test_scope_resolver_exposes_tools_for_model_driven_selection():
    result = tool_scope_resolver.resolve(
        classification=_classification("DIRECT_CHAT", query_subtype="smalltalk", allow_direct_answer=True),
        tool_schemas=[_schema("builtin/websearch")],
        tool_catalog_entries=[
            {"id": "builtin/websearch", "domains": ["web_search"], "allowed_intents": ["TOOL_REQUIRED"], "side_effect": "external_read"}
        ],
    )

    assert [item["function"]["name"] for item in result] == ["builtin/websearch"]


def test_scope_resolver_does_not_select_tools_by_domain_keywords():
    result = tool_scope_resolver.resolve(
        classification=_classification("TOOL_REQUIRED", candidate_tool_domains=["web_search"]),
        tool_schemas=[_schema("builtin/websearch"), _schema("builtin/python_exec")],
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

    assert [item["function"]["name"] for item in result] == ["builtin/websearch", "builtin/python_exec"]


def test_scope_resolver_defers_high_risk_confirmation_to_tool_policy_gate():
    result = tool_scope_resolver.resolve(
        classification=_classification("TOOL_REQUIRED", candidate_tool_domains=["python"]),
        tool_schemas=[_schema("builtin/python_exec")],
        tool_catalog_entries=[
            {
                "id": "builtin/python_exec",
                "risk_level": "high",
                "side_effect": "write",
                "requires_confirmation": True,
                "allowed_intents": ["TOOL_REQUIRED"],
                "domains": ["python"],
            }
        ],
    )

    assert [item["function"]["name"] for item in result] == ["builtin/python_exec"]
