from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List

from backend.services.agent_runtime_defaults import default_agent_tool_ids


@dataclass(slots=True)
class ResolvedAgentRuntime:
    agent_id: str
    agent_config: Dict[str, Any]
    supports_tools: bool
    tool_schemas: List[Dict[str, Any]]
    resolved_tool_names: List[str]
    max_steps: int
    tool_catalog_entries: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_tools: List[str] = field(default_factory=list)
    configured_tools: List[str] = field(default_factory=list)
    bound_tool_ids: List[str] = field(default_factory=list)
    requested_tool_names: List[str] = field(default_factory=list)
    unavailable_requested_tools: List[str] = field(default_factory=list)
    binding_drift: Dict[str, List[str]] = field(default_factory=dict)
    resolution_source: str = "bindings"


class AgentRuntimeAssembler:
    """Assembles the agent runtime from agent config, bindings, and the tool catalog."""

    def __init__(self, runtime_backend: Any, *, default_max_steps: int = 6) -> None:
        self.runtime_backend = runtime_backend
        self.default_max_steps = default_max_steps

    async def assemble(
        self,
        *,
        agent_id: str,
        agent_config: Dict[str, Any],
        user_input: str,
    ) -> ResolvedAgentRuntime:
        configured_tools = self._normalize_tool_ids(agent_config.get("tools") or [])
        has_explicit_tool_config = "tools" in agent_config
        capability_flags = agent_config.get("capability_flags") if isinstance(agent_config.get("capability_flags"), dict) else {}
        supports_tools = not bool(capability_flags.get("tools_disabled", False))
        max_steps = int((agent_config.get("constraints") or {}).get("max_steps", self.default_max_steps))

        resolution_source = "bindings"
        binding_drift: Dict[str, List[str]] = {}
        unresolved_tools: List[str] = []

        config_resolution = await self.runtime_backend.validate_tool_ids(configured_tools) if configured_tools else None
        if config_resolution is not None and config_resolution.missing_tool_ids:
            unresolved_tools.extend(config_resolution.missing_tool_ids)

        bound_tool_ids = await self.runtime_backend.get_agent_tool_ids(agent_id)
        if has_explicit_tool_config and not configured_tools:
            # Explicit tools=[] must win over any stale bindings from older saves.
            if bound_tool_ids:
                binding_drift["binding_only"] = list(bound_tool_ids)
            bound_tool_ids = []
            resolution_source = "explicit_empty_tools"
        elif supports_tools and not configured_tools and not bound_tool_ids:
            default_tools = default_agent_tool_ids()
            sync_result = await self.runtime_backend.apply_default_agent_tools(agent_id, default_tools)
            configured_tools = list(default_tools)
            bound_tool_ids = list(sync_result.resolved_tool_ids)
            config_resolution = await self.runtime_backend.validate_tool_ids(configured_tools)
            resolution_source = "default_builtin_profile"

        if not bound_tool_ids and configured_tools:
            if config_resolution is not None and not config_resolution.missing_tool_ids and config_resolution.resolved_tool_ids:
                sync_result = await self.runtime_backend.sync_agent_tools(agent_id, configured_tools)
                bound_tool_ids = list(sync_result.resolved_tool_ids)
                if resolution_source == "bindings":
                    resolution_source = "legacy_config_sync"
            else:
                resolution_source = "binding_drift"

        if config_resolution is not None:
            config_only = [tool_id for tool_id in config_resolution.resolved_tool_ids if tool_id not in bound_tool_ids]
            binding_only = [tool_id for tool_id in bound_tool_ids if tool_id not in config_resolution.resolved_tool_ids]
            if config_only:
                binding_drift["config_only"] = config_only
            if binding_only:
                binding_drift["binding_only"] = binding_only

        catalog_entries = await self.runtime_backend.get_tool_catalog_entries(bound_tool_ids)
        tool_schemas = [entry.get("openai_schema", {}) for entry in catalog_entries if entry.get("openai_schema")]
        resolved_tool_names = self._extract_tool_names(tool_schemas)

        global_schemas = await self.runtime_backend.get_all_tools_schema()
        requested_tool_names = self._select_requested_tools(user_input, self._extract_tool_names(global_schemas))
        unavailable_requested_tools = [
            tool_name for tool_name in requested_tool_names if tool_name not in resolved_tool_names
        ]

        return ResolvedAgentRuntime(
            agent_id=agent_id,
            agent_config=agent_config,
            supports_tools=supports_tools,
            tool_schemas=tool_schemas,
            tool_catalog_entries=catalog_entries,
            resolved_tool_names=resolved_tool_names,
            max_steps=max_steps,
            unresolved_tools=sorted(set(unresolved_tools)),
            configured_tools=configured_tools,
            bound_tool_ids=bound_tool_ids,
            requested_tool_names=requested_tool_names,
            unavailable_requested_tools=unavailable_requested_tools,
            binding_drift=binding_drift,
            resolution_source=resolution_source,
        )

    @staticmethod
    def _normalize_tool_ids(tool_ids: List[str]) -> List[str]:
        normalized: List[str] = []
        seen: set[str] = set()
        for tool_id in tool_ids:
            if not isinstance(tool_id, str):
                continue
            candidate = tool_id.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        return normalized

    @staticmethod
    def _extract_tool_names(tools: List[Dict[str, Any]]) -> List[str]:
        tool_names = [
            str(((tool.get("function") or {}).get("name", ""))).strip()
            for tool in tools
            if isinstance(tool, dict)
        ]
        return [name for name in tool_names if name]

    @classmethod
    def _select_requested_tools(cls, user_input: str, tool_names: List[str]) -> List[str]:
        normalized_input = user_input.lower()
        matches: List[str] = []
        for tool_name in tool_names:
            bare_name = tool_name.split("/", 1)[-1]
            if cls._contains_explicit_tool_reference(normalized_input, tool_name.lower()) or cls._contains_explicit_tool_reference(normalized_input, bare_name.lower()):
                matches.append(tool_name)
        return matches

    @staticmethod
    def _contains_explicit_tool_reference(user_input: str, tool_token: str) -> bool:
        pattern = rf"(?<![a-z0-9_]){re.escape(tool_token)}(?![a-z0-9_])"
        return bool(re.search(pattern, user_input))
