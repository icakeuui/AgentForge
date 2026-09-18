from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from plugin_marketplace.db.database import session_scope
from plugin_marketplace.db.models import Extension, Tool, UserExtension
from plugin_marketplace.exceptions import ToolNotFoundError
from plugin_marketplace.interfaces import ToolDescriptor, ToolType


class ToolRegistry:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def upsert_tools(self, extension_id: str, tools: Sequence[ToolDescriptor]) -> List[Tool]:
        async with session_scope(self.session_factory) as session:
            await session.execute(delete(Tool).where(Tool.extension_id == extension_id))
            persisted: List[Tool] = []
            for tool in tools:
                db_tool = Tool(
                    extension_id=extension_id,
                    name=tool.name,
                    display_name=tool.display_name,
                    description=tool.description,
                    input_schema=tool.input_schema,
                    output_schema=tool.output_schema,
                    mcp_tool_name=tool.mcp_tool_name,
                    risk_level=tool.risk_level,
                    side_effect=tool.side_effect,
                    requires_confirmation=tool.requires_confirmation,
                    allowed_intents=tool.allowed_intents,
                    domains=tool.domains,
                    requires_auth_scope=tool.requires_auth_scope,
                    max_calls_per_run=tool.max_calls_per_run,
                    timeout_ms=tool.timeout_ms,
                    returns_sensitive_data=tool.returns_sensitive_data,
                    audit_payload_level=tool.audit_payload_level,
                )
                session.add(db_tool)
                persisted.append(db_tool)
            await session.flush()
            return persisted

    async def list_tools(
        self,
        user_id: Optional[str] = None,
        extension_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        async with self.session_factory() as session:
            stmt = select(Tool, Extension).join(Extension, Tool.extension_id == Extension.id).where(Tool.enabled.is_(True))
            if extension_id:
                stmt = stmt.where(Tool.extension_id == extension_id)
            if user_id:
                stmt = stmt.join(
                    UserExtension,
                    (UserExtension.extension_id == Extension.id) & (UserExtension.user_id == user_id),
                ).where(UserExtension.status.in_(["running", "installed"]))
            result = await session.execute(stmt)
            rows = result.all()
            return [self._serialize_tool(tool, extension) for tool, extension in rows]

    async def get_tool(self, compound_name: str) -> Dict[str, Any]:
        extension_id, tool_name = compound_name.split("/", 1)
        async with self.session_factory() as session:
            stmt = (
                select(Tool, Extension)
                .join(Extension, Tool.extension_id == Extension.id)
                .where(Tool.extension_id == extension_id, Tool.name == tool_name)
            )
            row = (await session.execute(stmt)).first()
            if not row:
                raise ToolNotFoundError(f"Tool {compound_name} not found.")
            return self._serialize_tool(row[0], row[1])

    async def get_tools(self, compound_names: Sequence[str]) -> List[Dict[str, Any]]:
        normalized = [name.strip() for name in compound_names if isinstance(name, str) and name.strip()]
        if not normalized:
            return []

        conditions = []
        for compound_name in normalized:
            extension_id, tool_name = compound_name.split("/", 1)
            conditions.append((Tool.extension_id == extension_id) & (Tool.name == tool_name))

        async with self.session_factory() as session:
            stmt = (
                select(Tool, Extension)
                .join(Extension, Tool.extension_id == Extension.id)
                .where(or_(*conditions))
            )
            rows = (await session.execute(stmt)).all()

        tools_by_id = {f"{tool.extension_id}/{tool.name}": self._serialize_tool(tool, extension) for tool, extension in rows}
        return [tools_by_id[name] for name in normalized if name in tools_by_id]

    def _serialize_tool(self, tool: Tool, extension: Extension) -> Dict[str, Any]:
        descriptor = ToolDescriptor(
            extension_id_value=extension.id,
            name_value=tool.name,
            description_value=tool.description or tool.name,
            tool_type_value=ToolType(extension.tool_type),
            input_schema_value=tool.input_schema or {"type": "object", "properties": {}},
            output_schema_value=tool.output_schema or {"type": "object"},
            display_name=tool.display_name,
            mcp_tool_name=tool.mcp_tool_name,
            risk_level=tool.risk_level or "medium",
            side_effect=tool.side_effect or "read",
            requires_confirmation=bool(tool.requires_confirmation),
            allowed_intents=tool.allowed_intents or ["TOOL_REQUIRED", "TOOL_OPTIONAL"],
            domains=tool.domains or [],
            requires_auth_scope=tool.requires_auth_scope or [],
            max_calls_per_run=tool.max_calls_per_run or 2,
            timeout_ms=tool.timeout_ms or 10000,
            returns_sensitive_data=bool(tool.returns_sensitive_data),
            audit_payload_level=tool.audit_payload_level or "summary",
        )
        return {
            "tool_db_id": tool.id,
            "id": descriptor.id,
            "name": descriptor.name,
            "description": descriptor.description,
            "extension_id": extension.id,
            "extension_name": extension.name,
            "tool_type": extension.tool_type,
            "input_schema": descriptor.input_schema,
            "output_schema": descriptor.output_schema,
            "display_name": tool.display_name,
            "mcp_tool_name": tool.mcp_tool_name,
            "risk_level": descriptor.risk_level,
            "side_effect": descriptor.side_effect,
            "requires_confirmation": descriptor.requires_confirmation,
            "allowed_intents": descriptor.allowed_intents,
            "domains": descriptor.domains,
            "requires_auth_scope": descriptor.requires_auth_scope,
            "max_calls_per_run": descriptor.max_calls_per_run,
            "timeout_ms": descriptor.timeout_ms,
            "returns_sensitive_data": descriptor.returns_sensitive_data,
            "audit_payload_level": descriptor.audit_payload_level,
            "openai_schema": descriptor.to_openai_schema(),
        }
