from __future__ import annotations

from typing import Any, Dict, List

from backend.models.schemas import IntentClassificationResult
from backend.services.policy_gate import policy_gate


class ToolScopeResolver:
    """Resolve the OpenAI tool schemas allowed for the current turn."""

    def resolve(
        self,
        *,
        classification: IntentClassificationResult,
        tool_schemas: List[Dict[str, Any]],
        tool_catalog_entries: List[Dict[str, Any]],
        confirmed_tool_actions: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, Any]]:
        tool_ids = [entry.get("id") for entry in tool_catalog_entries if isinstance(entry.get("id"), str)]
        if not tool_ids:
            tool_ids = [
                str(((schema.get("function") or {}).get("name", ""))).strip()
                for schema in tool_schemas
                if isinstance(schema, dict)
            ]
        allowed_ids = policy_gate._allowed_tools_for_intent(
            classification=classification,
            bound_tool_ids=tool_ids,
            tool_catalog_entries=tool_catalog_entries,
            confirmed_tool_actions=confirmed_tool_actions or [],
        )
        allowed = set(allowed_ids)
        return [
            schema
            for schema in tool_schemas
            if str(((schema.get("function") or {}).get("name", ""))).strip() in allowed
        ]


tool_scope_resolver = ToolScopeResolver()
