"""
plugin_marketplace.core.binding
Agent-tool binding service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from plugin_marketplace.db import PMAgentTool, PMTool
from plugin_marketplace.exceptions import ToolBindingValidationError


@dataclass(slots=True)
class ToolResolutionResult:
    requested_tool_ids: List[str]
    resolved_tool_ids: List[str] = field(default_factory=list)
    missing_tool_ids: List[str] = field(default_factory=list)
    resolution_map: Dict[str, str] = field(default_factory=dict)
    duplicate_tool_ids: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.missing_tool_ids and self.resolved_tool_ids:
            return "partial_failure"
        if self.missing_tool_ids:
            return "failed"
        return "success"


@dataclass(slots=True)
class ToolBindingResult:
    requested_tool_ids: List[str]
    resolved_tool_ids: List[str]
    missing_tool_ids: List[str] = field(default_factory=list)
    duplicate_tool_ids: List[str] = field(default_factory=list)
    already_bound_tool_ids: List[str] = field(default_factory=list)
    bound_tool_ids: List[str] = field(default_factory=list)
    unbound_tool_ids: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.missing_tool_ids and (self.bound_tool_ids or self.already_bound_tool_ids or self.unbound_tool_ids):
            return "partial_failure"
        if self.missing_tool_ids:
            return "failed"
        return "success"


class AgentToolBindingService:
    """Manages which tools are bound to which agents."""

    def __init__(self, session_or_factory):
        if isinstance(session_or_factory, async_sessionmaker):
            self._session_factory = session_or_factory
            self._session = None
        else:
            self._session = session_or_factory
            self._session_factory = None

    async def _get_session(self) -> AsyncSession:
        if self._session_factory:
            return self._session_factory()
        return self._session

    async def _close_session(self, session: AsyncSession) -> None:
        if self._session_factory:
            await session.close()

    async def resolve_tool_ids(self, tool_ids: List[str]) -> ToolResolutionResult:
        session = await self._get_session()
        try:
            resolved_tool_ids: List[str] = []
            missing_tool_ids: List[str] = []
            resolution_map: Dict[str, str] = {}
            duplicate_tool_ids: List[str] = []
            seen_canonical: set[str] = set()

            for raw_tool_id in tool_ids:
                normalized_input = str(raw_tool_id).strip()
                if not normalized_input:
                    missing_tool_ids.append(normalized_input)
                    continue

                tool = await self._resolve_tool_record(session, normalized_input)
                if tool is None:
                    missing_tool_ids.append(normalized_input)
                    continue

                canonical_tool_id = f"{tool.extension_id}/{tool.name}"
                resolution_map[normalized_input] = canonical_tool_id
                if canonical_tool_id in seen_canonical:
                    duplicate_tool_ids.append(canonical_tool_id)
                    continue

                seen_canonical.add(canonical_tool_id)
                resolved_tool_ids.append(canonical_tool_id)

            return ToolResolutionResult(
                requested_tool_ids=[str(tool_id).strip() for tool_id in tool_ids],
                resolved_tool_ids=resolved_tool_ids,
                missing_tool_ids=missing_tool_ids,
                resolution_map=resolution_map,
                duplicate_tool_ids=duplicate_tool_ids,
            )
        finally:
            await self._close_session(session)

    async def bind_tools(self, agent_id: str, tool_ids: List[str], *, strict: bool = True) -> ToolBindingResult:
        """
        Bind tools to an agent.
        """
        resolution = await self.resolve_tool_ids(tool_ids)
        if strict and resolution.missing_tool_ids:
            raise ToolBindingValidationError(
                f"Unknown tool ids: {', '.join(resolution.missing_tool_ids)}",
                missing_tool_ids=resolution.missing_tool_ids,
                resolved_tool_ids=resolution.resolved_tool_ids,
            )

        session = await self._get_session()
        try:
            already_bound: List[str] = []
            newly_bound: List[str] = []

            for tool_id in resolution.resolved_tool_ids:
                tool_db_id = await self._resolve_tool_db_id(session, tool_id)
                if tool_db_id is None:
                    continue

                query = select(PMAgentTool).where(
                    and_(
                        PMAgentTool.agent_id == agent_id,
                        PMAgentTool.tool_id == tool_db_id,
                    )
                )
                existing = (await session.execute(query)).scalar_one_or_none()
                if existing:
                    already_bound.append(tool_id)
                    continue

                session.add(
                    PMAgentTool(
                        agent_id=agent_id,
                        tool_id=tool_db_id,
                        enabled=True,
                    )
                )
                newly_bound.append(tool_id)

            await session.commit()
            return ToolBindingResult(
                requested_tool_ids=resolution.requested_tool_ids,
                resolved_tool_ids=resolution.resolved_tool_ids,
                missing_tool_ids=resolution.missing_tool_ids,
                duplicate_tool_ids=resolution.duplicate_tool_ids,
                already_bound_tool_ids=already_bound,
                bound_tool_ids=newly_bound,
            )
        finally:
            await self._close_session(session)

    async def replace_tools(self, agent_id: str, tool_ids: List[str], *, strict: bool = True) -> ToolBindingResult:
        """
        Replace the entire bound tool set for an agent.
        """
        resolution = await self.resolve_tool_ids(tool_ids)
        if strict and resolution.missing_tool_ids:
            raise ToolBindingValidationError(
                f"Unknown tool ids: {', '.join(resolution.missing_tool_ids)}",
                missing_tool_ids=resolution.missing_tool_ids,
                resolved_tool_ids=resolution.resolved_tool_ids,
            )

        session = await self._get_session()
        try:
            current_rows = await self._get_agent_tool_rows(session, agent_id)
            current_by_id = {f"{tool.extension_id}/{tool.name}": binding for binding, tool in current_rows}

            desired_tool_ids = set(resolution.resolved_tool_ids)
            unbound_tool_ids: List[str] = []
            already_bound: List[str] = []
            newly_bound: List[str] = []

            for tool_id, binding in current_by_id.items():
                if tool_id not in desired_tool_ids:
                    await session.delete(binding)
                    unbound_tool_ids.append(tool_id)

            for tool_id in resolution.resolved_tool_ids:
                if tool_id in current_by_id:
                    already_bound.append(tool_id)
                    continue

                tool_db_id = await self._resolve_tool_db_id(session, tool_id)
                if tool_db_id is None:
                    continue

                session.add(
                    PMAgentTool(
                        agent_id=agent_id,
                        tool_id=tool_db_id,
                        enabled=True,
                    )
                )
                newly_bound.append(tool_id)

            await session.commit()
            return ToolBindingResult(
                requested_tool_ids=resolution.requested_tool_ids,
                resolved_tool_ids=resolution.resolved_tool_ids,
                missing_tool_ids=resolution.missing_tool_ids,
                duplicate_tool_ids=resolution.duplicate_tool_ids,
                already_bound_tool_ids=already_bound,
                bound_tool_ids=newly_bound,
                unbound_tool_ids=unbound_tool_ids,
            )
        finally:
            await self._close_session(session)

    async def unbind_tools(self, agent_id: str, tool_ids: List[str], *, strict: bool = True) -> ToolBindingResult:
        """
        Unbind tools from an agent.
        """
        resolution = await self.resolve_tool_ids(tool_ids)
        if strict and resolution.missing_tool_ids:
            raise ToolBindingValidationError(
                f"Unknown tool ids: {', '.join(resolution.missing_tool_ids)}",
                missing_tool_ids=resolution.missing_tool_ids,
                resolved_tool_ids=resolution.resolved_tool_ids,
            )

        session = await self._get_session()
        try:
            removed_tool_ids: List[str] = []
            for tool_id in resolution.resolved_tool_ids:
                tool_db_id = await self._resolve_tool_db_id(session, tool_id)
                if tool_db_id is None:
                    continue

                query = select(PMAgentTool).where(
                    and_(
                        PMAgentTool.agent_id == agent_id,
                        PMAgentTool.tool_id == tool_db_id,
                    )
                )
                binding = (await session.execute(query)).scalar_one_or_none()
                if binding:
                    await session.delete(binding)
                    removed_tool_ids.append(tool_id)

            await session.commit()
            return ToolBindingResult(
                requested_tool_ids=resolution.requested_tool_ids,
                resolved_tool_ids=resolution.resolved_tool_ids,
                missing_tool_ids=resolution.missing_tool_ids,
                duplicate_tool_ids=resolution.duplicate_tool_ids,
                unbound_tool_ids=removed_tool_ids,
            )
        finally:
            await self._close_session(session)

    async def get_agent_tools(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get all tools bound to an agent.
        Returns tool schemas in OpenAI function calling format.
        """
        session = await self._get_session()
        try:
            rows = await self._get_agent_tool_rows(session, agent_id)
            tools = []
            for _binding, tool in rows:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": f"{tool.extension_id}/{tool.name}",
                            "description": tool.description or "",
                            "parameters": tool.input_schema or {"type": "object", "properties": {}},
                        },
                    }
                )
            return tools
        finally:
            await self._close_session(session)

    async def get_agent_tool_ids(self, agent_id: str) -> List[str]:
        session = await self._get_session()
        try:
            rows = await self._get_agent_tool_rows(session, agent_id)
            return [f"{tool.extension_id}/{tool.name}" for _binding, tool in rows]
        finally:
            await self._close_session(session)

    async def _get_agent_tool_rows(self, session: AsyncSession, agent_id: str) -> List[Any]:
        query = (
            select(PMAgentTool, PMTool)
            .join(PMTool, PMAgentTool.tool_id == PMTool.id)
            .where(
                and_(
                    PMAgentTool.agent_id == agent_id,
                    PMAgentTool.enabled.is_(True),
                    PMTool.enabled.is_(True),
                )
            )
        )
        result = await session.execute(query)
        return result.all()

    async def _resolve_tool_db_id(self, session: AsyncSession, tool_id: str) -> Optional[str]:
        tool = await self._resolve_tool_record(session, tool_id)
        return tool.id if tool else None

    async def _resolve_tool_record(self, session: AsyncSession, tool_id: str) -> Optional[PMTool]:
        normalized = tool_id.strip()
        if not normalized:
            return None

        query = select(PMTool).where(PMTool.id == normalized)
        tool = (await session.execute(query)).scalar_one_or_none()
        if tool:
            return tool

        parts = normalized.split("/", 1)
        if len(parts) == 2:
            ext_id, tool_name = parts
            query = select(PMTool).where(
                and_(
                    PMTool.extension_id == ext_id,
                    PMTool.name == tool_name,
                )
            )
            tool = (await session.execute(query)).scalar_one_or_none()
            if tool:
                return tool

        query = select(PMTool).where(PMTool.name == normalized)
        matches = list((await session.execute(query)).scalars().all())
        if len(matches) == 1:
            return matches[0]
        builtin_match = next((candidate for candidate in matches if candidate.extension_id == "builtin"), None)
        if builtin_match:
            return builtin_match
        return None
