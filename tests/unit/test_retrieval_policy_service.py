from backend.models.schemas import IntentClassificationResult
from backend.services.retrieval_policy_service import retrieval_policy_service


def _classification(intent_type: str, query_subtype: str = "smalltalk") -> IntentClassificationResult:
    return IntentClassificationResult(
        intent_type=intent_type,
        query_subtype=query_subtype,
        confidence=0.9,
    )


def test_direct_chat_has_no_retrieval():
    policy = retrieval_policy_service.resolve(_classification("DIRECT_CHAT"))

    assert policy.retrieval_mode == "none"
    assert policy.required is False
    assert policy.limit == 0


def test_exact_clause_is_required_exact_retrieval():
    policy = retrieval_policy_service.resolve(_classification("KB_REQUIRED", "exact_clause"))

    assert policy.retrieval_mode == "exact_clause"
    assert policy.required is True
    assert policy.min_score == 1.0


def test_kb_required_uses_required_hybrid():
    policy = retrieval_policy_service.resolve(_classification("KB_REQUIRED", "policy_explanation"))

    assert policy.retrieval_mode == "required_hybrid"
    assert policy.required is True


def test_kb_optional_uses_optional_hybrid():
    policy = retrieval_policy_service.resolve(_classification("KB_OPTIONAL", "fact_lookup"))

    assert policy.retrieval_mode == "optional_hybrid"
    assert policy.required is False
