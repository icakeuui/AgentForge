from __future__ import annotations

from backend.models.schemas import IntentClassificationResult, RetrievalPolicy


class RetrievalPolicyService:
    VERSION = "retrieval-policy-v1"

    def resolve(self, classification: IntentClassificationResult) -> RetrievalPolicy:
        if classification.intent_type == "DIRECT_CHAT":
            return RetrievalPolicy(retrieval_mode="none", limit=0, min_score=0.0, required=False)
        if classification.query_subtype == "exact_clause":
            return RetrievalPolicy(retrieval_mode="exact_clause", limit=4, min_score=1.0, required=True)
        if classification.intent_type == "KB_REQUIRED":
            return RetrievalPolicy(retrieval_mode="required_hybrid", limit=4, min_score=2.0, required=True)
        if classification.intent_type == "KB_OPTIONAL":
            return RetrievalPolicy(retrieval_mode="optional_hybrid", limit=4, min_score=2.0, required=False)
        return RetrievalPolicy(retrieval_mode="none", limit=0, min_score=0.0, required=False)


retrieval_policy_service = RetrievalPolicyService()
