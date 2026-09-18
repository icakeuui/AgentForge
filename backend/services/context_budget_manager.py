from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.models.schemas import Message


DEFAULT_CONTEXT_WINDOW = 8192
DEFAULT_RESERVED_COMPLETION_TOKENS = 1024
DEFAULT_SAFETY_MARGIN_RATIO = 0.08
MIN_SAFETY_MARGIN_TOKENS = 256
MIN_PROMPT_BUDGET_TOKENS = 3072
MAX_TOOL_OBSERVATION_CHARS = 6000

MODEL_CONTEXT_WINDOWS: Dict[str, int] = {
    "gpt-3.5-turbo": 16385,
    "gpt-4": 8192,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4.1": 1047576,
    "gpt-4.1-mini": 1047576,
    "gpt-4.1-nano": 1047576,
    "o3": 200000,
    "o3-mini": 200000,
    "o4-mini": 200000,
}


@dataclass
class ContextBudgetReport:
    context_limit: int
    reserved_completion_tokens: int
    safety_margin_tokens: int
    prompt_budget: int
    estimated_prompt_tokens_before: int
    estimated_prompt_tokens_after: int
    tools_tokens: int
    messages_tokens_before: int
    messages_tokens_after: int
    dropped_messages_count: int = 0
    truncated_tool_observations_count: int = 0
    budget_status: str = "ok"
    usage_estimated: bool = True
    notes: List[str] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return {
            "context_limit": self.context_limit,
            "reserved_completion_tokens": self.reserved_completion_tokens,
            "safety_margin_tokens": self.safety_margin_tokens,
            "prompt_budget": self.prompt_budget,
            "estimated_prompt_tokens_before": self.estimated_prompt_tokens_before,
            "estimated_prompt_tokens_after": self.estimated_prompt_tokens_after,
            "tools_tokens": self.tools_tokens,
            "messages_tokens_before": self.messages_tokens_before,
            "messages_tokens_after": self.messages_tokens_after,
            "dropped_messages_count": self.dropped_messages_count,
            "truncated_tool_observations_count": self.truncated_tool_observations_count,
            "budget_status": self.budget_status,
            "usage_estimated": self.usage_estimated,
            "notes": list(self.notes),
        }


@dataclass
class ContextBudgetResult:
    messages: List[Message]
    tools: List[Dict[str, Any]]
    report: ContextBudgetReport
    exceeded: bool = False


class ContextBudgetManager:
    """
    Per-call context budget guard.

    This service deliberately stays outside ModelGateway so provider calls remain
    stateless and business-free. It estimates request size, trims old chat
    history before the latest user turn, and refuses calls that still cannot fit.
    """

    def fit(
        self,
        *,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]],
        model_name: str,
        max_completion_tokens: Optional[int],
        runtime_config: Optional[Dict[str, Any]] = None,
    ) -> ContextBudgetResult:
        runtime_config = runtime_config or {}
        tool_payload = list(tools or [])
        context_limit = self._resolve_context_window(model_name, runtime_config)
        requested_reserved_completion_tokens = self._resolve_reserved_completion_tokens(
            max_completion_tokens=max_completion_tokens,
            runtime_config=runtime_config,
        )
        safety_margin_tokens = max(
            MIN_SAFETY_MARGIN_TOKENS,
            int(context_limit * DEFAULT_SAFETY_MARGIN_RATIO),
        )
        max_reserved_completion_tokens = max(1, context_limit - safety_margin_tokens - MIN_PROMPT_BUDGET_TOKENS)
        reserved_completion_tokens = min(requested_reserved_completion_tokens, max_reserved_completion_tokens)
        prompt_budget = max(1, context_limit - reserved_completion_tokens - safety_margin_tokens)

        normalized_messages, truncated_observations = self._truncate_large_tool_observations(messages)
        tools_tokens = self.estimate_tools_tokens(tool_payload)
        messages_tokens_before = self.estimate_messages_tokens(messages)
        normalized_tokens = self.estimate_messages_tokens(normalized_messages)
        estimated_before = messages_tokens_before + tools_tokens

        fitted_messages, dropped_count = self._drop_old_history_to_fit(
            messages=normalized_messages,
            max_message_tokens=max(1, prompt_budget - tools_tokens),
        )
        messages_tokens_after = self.estimate_messages_tokens(fitted_messages)
        estimated_after = messages_tokens_after + tools_tokens

        notes: List[str] = []
        if truncated_observations:
            notes.append("large_tool_observations_truncated")
        if dropped_count:
            notes.append("old_conversation_history_dropped")
        if reserved_completion_tokens < requested_reserved_completion_tokens:
            notes.append("reserved_completion_tokens_capped_to_context_window")

        exceeded = estimated_after > prompt_budget
        budget_status = "exceeded" if exceeded else ("trimmed" if notes else "ok")
        if exceeded:
            notes.append("minimum_required_context_exceeds_prompt_budget")

        report = ContextBudgetReport(
            context_limit=context_limit,
            reserved_completion_tokens=reserved_completion_tokens,
            safety_margin_tokens=safety_margin_tokens,
            prompt_budget=prompt_budget,
            estimated_prompt_tokens_before=estimated_before,
            estimated_prompt_tokens_after=estimated_after,
            tools_tokens=tools_tokens,
            messages_tokens_before=messages_tokens_before,
            messages_tokens_after=messages_tokens_after,
            dropped_messages_count=dropped_count,
            truncated_tool_observations_count=truncated_observations,
            budget_status=budget_status,
            notes=notes,
        )
        return ContextBudgetResult(
            messages=fitted_messages,
            tools=tool_payload,
            report=report,
            exceeded=exceeded,
        )

    def estimate_messages_tokens(self, messages: List[Message]) -> int:
        return sum(self.estimate_message_tokens(message) for message in messages)

    def estimate_message_tokens(self, message: Message) -> int:
        payload_tokens = 4
        payload_tokens += self.estimate_text_tokens(message.role)
        payload_tokens += self.estimate_text_tokens(message.content or "")
        payload_tokens += self.estimate_text_tokens(message.reasoning_content or "")
        payload_tokens += self.estimate_text_tokens(message.name or "")
        payload_tokens += self.estimate_text_tokens(message.tool_call_id or "")
        if message.tool_calls:
            payload_tokens += self.estimate_text_tokens(
                json.dumps([tool_call.model_dump() for tool_call in message.tool_calls], ensure_ascii=False)
            )
        return payload_tokens

    def estimate_tools_tokens(self, tools: List[Dict[str, Any]]) -> int:
        if not tools:
            return 0
        return self.estimate_text_tokens(json.dumps(tools, ensure_ascii=False))

    def estimate_text_tokens(self, text: str) -> int:
        if not text:
            return 0
        ascii_chars = len(re.findall(r"[\x00-\x7F]", text))
        non_ascii_chars = len(text) - ascii_chars
        ascii_tokens = max(1, ascii_chars // 4) if ascii_chars else 0
        non_ascii_tokens = int(non_ascii_chars * 1.2)
        return max(1, ascii_tokens + non_ascii_tokens)

    def _resolve_context_window(self, model_name: str, runtime_config: Dict[str, Any]) -> int:
        configured = runtime_config.get("context_window") or runtime_config.get("context_window_tokens")
        if isinstance(configured, int) and configured > 0:
            return configured

        normalized_models = self._normalized_model_candidates(model_name)
        for normalized_model in normalized_models:
            if normalized_model in MODEL_CONTEXT_WINDOWS:
                return MODEL_CONTEXT_WINDOWS[normalized_model]
            for known_model, context_window in MODEL_CONTEXT_WINDOWS.items():
                if normalized_model.startswith(known_model):
                    return context_window
        return DEFAULT_CONTEXT_WINDOW

    @staticmethod
    def _normalized_model_candidates(model_name: str) -> List[str]:
        normalized_model = (model_name or "").strip().lower()
        if not normalized_model:
            return []

        candidates = [normalized_model]
        if "/" in normalized_model:
            candidates.append(normalized_model.rsplit("/", 1)[-1])
        if ":" in normalized_model:
            candidates.append(normalized_model.rsplit(":", 1)[-1])
        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    def _resolve_reserved_completion_tokens(
        self,
        *,
        max_completion_tokens: Optional[int],
        runtime_config: Dict[str, Any],
    ) -> int:
        configured = runtime_config.get("reserved_completion_tokens")
        if isinstance(configured, int) and configured > 0:
            return configured
        if isinstance(max_completion_tokens, int) and max_completion_tokens > 0:
            return max_completion_tokens
        return DEFAULT_RESERVED_COMPLETION_TOKENS

    def _truncate_large_tool_observations(self, messages: List[Message]) -> tuple[List[Message], int]:
        normalized: List[Message] = []
        truncated_count = 0
        for message in messages:
            if message.role != "tool" or not message.content or len(message.content) <= MAX_TOOL_OBSERVATION_CHARS:
                normalized.append(message)
                continue
            truncated_count += 1
            preview = message.content[:MAX_TOOL_OBSERVATION_CHARS]
            normalized.append(
                message.model_copy(
                    update={
                        "content": json.dumps(
                            {
                                "truncated": True,
                                "original_chars": len(message.content),
                                "content_preview": preview,
                            },
                            ensure_ascii=False,
                        )
                    }
                )
            )
        return normalized, truncated_count

    def _drop_old_history_to_fit(
        self,
        *,
        messages: List[Message],
        max_message_tokens: int,
    ) -> tuple[List[Message], int]:
        if self.estimate_messages_tokens(messages) <= max_message_tokens:
            return messages, 0

        latest_user_index = self._latest_user_message_index(messages)
        if latest_user_index is None:
            return messages, 0

        system_messages = [message for message in messages[:latest_user_index] if message.role == "system"]
        history_messages = [message for message in messages[:latest_user_index] if message.role != "system"]
        required_tail = messages[latest_user_index:]

        kept_history: List[Message] = []
        required_tokens = self.estimate_messages_tokens(system_messages + required_tail)
        remaining_budget = max_message_tokens - required_tokens
        if remaining_budget > 0:
            for message in reversed(history_messages):
                message_tokens = self.estimate_message_tokens(message)
                if message_tokens <= remaining_budget:
                    kept_history.append(message)
                    remaining_budget -= message_tokens
            kept_history.reverse()

        dropped_count = len(history_messages) - len(kept_history)
        return [*system_messages, *kept_history, *required_tail], dropped_count

    def _latest_user_message_index(self, messages: List[Message]) -> Optional[int]:
        for index in range(len(messages) - 1, -1, -1):
            if messages[index].role == "user":
                return index
        return None


context_budget_manager = ContextBudgetManager()
