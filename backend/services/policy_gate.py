from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError

from backend.models.schemas import (
    BlockedToolDecision,
    FinalAnswerConstraints,
    FinalAnswerPolicyDecision,
    IntentClassificationResult,
    PolicyGateDecision,
    RetrievalPolicy,
    ToolPolicyDecision,
)


class PolicyGate:
    VERSION = "policy-gate-v2-tool-orchestration"

    def evaluate_pre_policy(
        self,
        *,
        classification: IntentClassificationResult,
        retrieval_policy: RetrievalPolicy,
        bound_tool_ids: List[str],
        tool_catalog_entries: List[Dict[str, Any]] | None = None,
        confirmed_tool_actions: List[Dict[str, Any]] | None = None,
    ) -> PolicyGateDecision:
        confirmed_tool_actions = confirmed_tool_actions or []
        allowed_tool_ids = self._allowed_tools_for_intent(
            classification=classification,
            bound_tool_ids=bound_tool_ids,
            tool_catalog_entries=tool_catalog_entries or [],
            confirmed_tool_actions=confirmed_tool_actions,
        )
        blocked_tool_ids = [
            BlockedToolDecision(
                tool_id=tool_id,
                reason_code="TOOL_NOT_ALLOWED_FOR_INTENT",
                reason_message=f"Tool is not allowed for {classification.intent_type}.",
            )
            for tool_id in bound_tool_ids
            if tool_id not in allowed_tool_ids
        ]
        return PolicyGateDecision(
            retrieval_required=retrieval_policy.required,
            retrieval_mode=retrieval_policy.retrieval_mode,
            direct_answer_allowed=classification.allow_direct_answer,
            requires_citation=classification.requires_citation,
            allowed_tool_ids_for_turn=allowed_tool_ids,
            blocked_tool_ids=blocked_tool_ids,
            requires_user_confirmation=False,
            final_answer_constraints=FinalAnswerConstraints(
                requires_citation=classification.requires_citation,
                evidence_required=classification.intent_type == "KB_REQUIRED",
                forbid_unverified_clause=classification.query_subtype == "exact_clause",
            ),
        )

    def evaluate_tool_call(
        self,
        *,
        tool_id: str,
        arguments: Dict[str, Any],
        classification: IntentClassificationResult | None,
        pre_policy: PolicyGateDecision | None,
        bound_tool_ids: List[str],
        tool_catalog_entries: List[Dict[str, Any]] | None = None,
        tool_call_counts: Dict[str, int],
        max_tool_calls: int,
        total_tool_calls_used: int,
        confirmed_tool_actions: List[Dict[str, Any]] | None = None,
    ) -> ToolPolicyDecision:
        if tool_id not in bound_tool_ids:
            return ToolPolicyDecision(
                allowed=False,
                reason_code="TOOL_NOT_BOUND",
                reason_message="Tool is not bound to this agent.",
                terminal=True,
            )
        if pre_policy is not None and tool_id not in pre_policy.allowed_tool_ids_for_turn:
            return ToolPolicyDecision(
                allowed=False,
                reason_code="TOOL_BLOCKED_BY_POLICY",
                reason_message="Tool is not in the policy-authorized tool set for this turn.",
                terminal=False,
            )
        if total_tool_calls_used >= max_tool_calls:
            return ToolPolicyDecision(
                allowed=False,
                reason_code="TOOL_CALL_BUDGET_EXCEEDED",
                reason_message="Run tool call budget has been exceeded.",
                terminal=True,
            )
        metadata = self.tool_metadata(tool_id, tool_catalog_entries=tool_catalog_entries or [])
        if tool_call_counts.get(tool_id, 0) >= int(metadata.get("max_calls_per_run", max_tool_calls)):
            return ToolPolicyDecision(
                allowed=False,
                reason_code="TOOL_CALL_BUDGET_EXCEEDED",
                reason_message="Per-tool call budget has been exceeded.",
                terminal=False,
            )
        if metadata["requires_confirmation"] and not self._has_confirmation(tool_id, arguments, confirmed_tool_actions or []):
            return ToolPolicyDecision(
                allowed=False,
                reason_code="TOOL_CONFIRMATION_REQUIRED",
                reason_message="This tool action requires user confirmation.",
                terminal=False,
            )
        schema_error = self._validate_arguments(arguments, metadata.get("input_schema"))
        if schema_error is not None:
            return ToolPolicyDecision(
                allowed=False,
                reason_code="TOOL_ARGUMENT_SCHEMA_INVALID",
                reason_message=schema_error,
                terminal=False,
            )
        return ToolPolicyDecision(allowed=True)

    def evaluate_final_answer(
        self,
        *,
        final_answer: str,
        classification: IntentClassificationResult | None,
        retrieval_result: Dict[str, Any] | None,
        tool_call_history: List[str],
    ) -> FinalAnswerPolicyDecision:
        if not classification:
            return FinalAnswerPolicyDecision(accepted=True)
        retrieval_result = retrieval_result or {}
        if classification.intent_type == "KB_REQUIRED" and retrieval_result.get("matched") is False:
            return FinalAnswerPolicyDecision(
                accepted=False,
                violation_code="ANSWER_WITHOUT_KB_MATCH",
                safe_final_answer=str(retrieval_result.get("knowledge_miss_answer") or "当前知识库未检索到对应内容。"),
                requires_retry=False,
            )
        if classification.requires_citation and retrieval_result.get("matched"):
            labels = [str(item.get("citation_label", "")) for item in retrieval_result.get("knowledge_hits", [])]
            if labels and not any(label and label in final_answer for label in labels):
                return FinalAnswerPolicyDecision(
                    accepted=False,
                    violation_code="MISSING_REQUIRED_CITATION",
                    safe_final_answer=f"{final_answer}\n\n来源：{', '.join(label for label in labels if label)}",
                    requires_retry=False,
                )
        sanitized_answer, sanitization_events = self.sanitize_final_answer(final_answer)
        if sanitization_events:
            pseudo_tool_events = {"pseudo_tool_call_block", "pseudo_tool_xml", "pseudo_tool_arg", "unexecuted_tool_call_text"}
            safe_answer = sanitized_answer
            if not tool_call_history and pseudo_tool_events.intersection(sanitization_events):
                safe_answer = "模型输出包含未执行的伪工具调用，已被系统拦截；本轮没有实际工具结果可用于回答。请确认 Agent 已启用并绑定所需工具后再运行。"
            return FinalAnswerPolicyDecision(
                accepted=False,
                violation_code="FINAL_ANSWER_SANITIZED",
                safe_final_answer=safe_answer
                or "模型输出包含内部推理内容，已被系统拦截；请重新生成最终答复。",
                requires_retry=False,
            )
        if not tool_call_history and any(phrase in sanitized_answer for phrase in ("我已查询", "我已提交", "我已删除", "已经查询", "已经提交", "已经删除")):
            return FinalAnswerPolicyDecision(
                accepted=False,
                violation_code="UNSUPPORTED_TOOL_RESULT_CLAIM",
                safe_final_answer="我没有实际调用外部工具，因此不能声称已经完成查询、提交或删除操作。",
                requires_retry=False,
            )
        return FinalAnswerPolicyDecision(accepted=True)

    @staticmethod
    def sanitize_final_answer(final_answer: str) -> tuple[str, List[str]]:
        """Strip private reasoning and textual pseudo tool-call artifacts from user-visible output."""
        text = final_answer or ""
        events: List[str] = []
        if not text:
            return "", events

        sanitized = text
        patterns = [
            ("reasoning_think_tag", r"<think\b[^>]*>.*?</think>"),
            ("pseudo_tool_call_block", r"\[TOOL_CALL\].*?(?:</tool_code>|$)"),
            ("pseudo_tool_xml", r"<tool_code>.*?</tool_code>"),
            ("pseudo_tool_arg", r"<arg>.*?</arg>"),
        ]
        for event, pattern in patterns:
            updated = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)
            if updated != sanitized:
                events.append(event)
                sanitized = updated

        leftover_markers = ("[TOOL_CALL]", "<tool_code", "</tool_code>", "<arg>", "</arg>", "<think", "</think>")
        if any(marker.lower() in sanitized.lower() for marker in leftover_markers):
            events.append("unexecuted_tool_call_text")
            for marker in leftover_markers:
                sanitized = sanitized.replace(marker, "")

        return sanitized.strip(), events

    @classmethod
    def _allowed_tools_for_intent(
        cls,
        *,
        classification: IntentClassificationResult,
        bound_tool_ids: List[str],
        tool_catalog_entries: List[Dict[str, Any]],
        confirmed_tool_actions: List[Dict[str, Any]],
    ) -> List[str]:
        if classification.intent_type in {"CLARIFY_REQUIRED", "UNSUPPORTED"}:
            return []
        allowed: List[str] = []
        for tool_id in bound_tool_ids:
            allowed.append(tool_id)
        return allowed

    @staticmethod
    def tool_metadata(tool_id: str, tool_catalog_entries: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
        name = tool_id.split("/", 1)[-1]
        defaults = {
            "risk_level": "medium",
            "side_effect": "read",
            "requires_confirmation": False,
            "allowed_intents": ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
            "domains": [name],
            "max_calls_per_run": 2,
            "input_schema": None,
        }
        for entry in tool_catalog_entries or []:
            if entry.get("id") != tool_id:
                continue
            return {
                **defaults,
                "risk_level": entry.get("risk_level") or defaults["risk_level"],
                "side_effect": entry.get("side_effect") or defaults["side_effect"],
                "requires_confirmation": bool(entry.get("requires_confirmation", defaults["requires_confirmation"])),
                "allowed_intents": entry.get("allowed_intents") or defaults["allowed_intents"],
                "domains": entry.get("domains") or defaults["domains"],
                "max_calls_per_run": int(entry.get("max_calls_per_run") or defaults["max_calls_per_run"]),
                "input_schema": entry.get("input_schema") or ((entry.get("openai_schema") or {}).get("function") or {}).get("parameters"),
            }
        if name in {"echo"}:
            return {**defaults, "risk_level": "low", "side_effect": "none", "allowed_intents": ["DIRECT_CHAT", "TOOL_OPTIONAL", "TOOL_REQUIRED"], "domains": ["utility"]}
        if name in {"calculate", "caculate"}:
            return {**defaults, "risk_level": "low", "side_effect": "none", "domains": ["calculator", "utility"]}
        if name in {"websearch", "web_search"}:
            return {**defaults, "risk_level": "medium", "side_effect": "external_read", "domains": ["web_search"]}
        if name == "python_exec":
            return {**defaults, "risk_level": "high", "side_effect": "write", "requires_confirmation": True, "domains": ["python"]}
        return defaults

    @staticmethod
    def arguments_hash(arguments: Dict[str, Any]) -> str:
        encoded = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @classmethod
    def _has_confirmation(cls, tool_id: str, arguments: Dict[str, Any], confirmations: List[Dict[str, Any]]) -> bool:
        expected_hash = cls.arguments_hash(arguments)
        return any(item.get("tool_id") == tool_id and item.get("arguments_hash") == expected_hash for item in confirmations)

    @staticmethod
    def _validate_arguments(arguments: Dict[str, Any], input_schema: Any) -> str | None:
        if not isinstance(input_schema, dict) or not input_schema:
            return None
        try:
            validator = Draft7Validator(input_schema)
            errors = sorted(validator.iter_errors(arguments), key=lambda error: list(error.path))
        except SchemaError as exc:
            return f"Tool input schema is invalid: {exc.message}"
        except Exception as exc:
            return f"Tool argument validation failed: {exc}"
        if not errors:
            return None
        return "; ".join(error.message for error in errors[:3])


policy_gate = PolicyGate()
