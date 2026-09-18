"""
plugin_marketplace.core.manager
Extension manager - handles install/uninstall lifecycle.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from datetime import datetime, timezone

from plugin_marketplace.db import PMExtension, PMUserExtension, Tool
from plugin_marketplace.interfaces import ExtensionEvents


class ExtensionManager:
    """Manages extension lifecycle: install, uninstall, status."""

    def __init__(
        self,
        session_or_factory,
        adapters: Dict[str, Any],
        events: Optional[ExtensionEvents] = None,
    ):
        if isinstance(session_or_factory, async_sessionmaker):
            self._session_factory = session_or_factory
            self._session = None
        else:
            self._session = session_or_factory
            self._session_factory = None
        self.adapters = adapters
        self.events = events or ExtensionEvents()

    async def _get_session(self) -> AsyncSession:
        if self._session_factory:
            return self._session_factory()
        return self._session

    async def _close_session(self, session: AsyncSession) -> None:
        if self._session_factory:
            await session.close()

    async def install(
        self,
        extension_id: str,
        user_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Install an extension for a user."""
        session = await self._get_session()
        try:
            # Get extension record
            query = select(PMExtension).where(PMExtension.id == extension_id)
            result = await session.execute(query)
            extension = result.scalar_one_or_none()
            if not extension:
                raise ValueError(f"Extension not found: {extension_id}")

            adapter_factory = self.adapters.get(extension_id)
            if adapter_factory is None:
                raise ValueError(f"No adapter available for extension: {extension_id}")
            adapter = adapter_factory(config or {})

            # Check if already installed for this user
            user_ext_query = select(PMUserExtension).where(
                PMUserExtension.user_id == user_id,
                PMUserExtension.extension_id == extension_id,
            )
            user_ext_result = await session.execute(user_ext_query)
            existing = user_ext_result.scalar_one_or_none()
            if existing:
                existing.config = config or {}
                existing.status = "installing"
                user_ext = existing
            else:
                user_ext = PMUserExtension(
                    user_id=user_id,
                    extension_id=extension_id,
                    status="installing",
                    config=config or {},
                )
                session.add(user_ext)

            # Register tools from adapter to database if not present
            tools = await adapter.list_tools()
            for tool_desc in tools:
                existing_tool_query = select(Tool).where(
                    Tool.extension_id == extension_id,
                    Tool.name == tool_desc.name,
                )
                existing_tool = (await session.execute(existing_tool_query)).scalar_one_or_none()
                if existing_tool:
                    existing_tool.description = tool_desc.description
                    existing_tool.input_schema = tool_desc.input_schema
                    existing_tool.risk_level = tool_desc.risk_level
                    existing_tool.side_effect = tool_desc.side_effect
                    existing_tool.requires_confirmation = tool_desc.requires_confirmation
                    existing_tool.allowed_intents = tool_desc.allowed_intents
                    existing_tool.domains = tool_desc.domains
                    existing_tool.requires_auth_scope = tool_desc.requires_auth_scope
                    existing_tool.max_calls_per_run = tool_desc.max_calls_per_run
                    existing_tool.timeout_ms = tool_desc.timeout_ms
                    existing_tool.returns_sensitive_data = tool_desc.returns_sensitive_data
                    existing_tool.audit_payload_level = tool_desc.audit_payload_level
                    existing_tool.enabled = True
                else:
                    tool = Tool(
                        id=tool_desc.id,
                        extension_id=extension_id,
                        name=tool_desc.name,
                        description=tool_desc.description,
                        enabled=True,
                        input_schema=tool_desc.input_schema,
                        risk_level=tool_desc.risk_level,
                        side_effect=tool_desc.side_effect,
                        requires_confirmation=tool_desc.requires_confirmation,
                        allowed_intents=tool_desc.allowed_intents,
                        domains=tool_desc.domains,
                        requires_auth_scope=tool_desc.requires_auth_scope,
                        max_calls_per_run=tool_desc.max_calls_per_run,
                        timeout_ms=tool_desc.timeout_ms,
                        returns_sensitive_data=tool_desc.returns_sensitive_data,
                        audit_payload_level=tool_desc.audit_payload_level,
                    )
                    session.add(tool)

            await session.commit()

            # Call adapter install
            try:
                await adapter.install()
                user_ext.status = "running"
                user_ext.started_at = datetime.now(timezone.utc)
            except Exception as e:
                user_ext.status = "error"
                user_ext.error_message = str(e)
                await session.commit()
                raise

            await session.commit()

            # Fire event
            try:
                await self.events.on_extension_installed(extension_id, user_id)
            except Exception:
                pass
        finally:
            await self._close_session(session)

    async def uninstall(self, extension_id: str, user_id: str) -> None:
        """Uninstall an extension for a user."""
        session = await self._get_session()
        try:
            query = select(PMUserExtension).where(
                PMUserExtension.user_id == user_id,
                PMUserExtension.extension_id == extension_id,
            )
            result = await session.execute(query)
            user_ext = result.scalar_one_or_none()
            if not user_ext:
                return  # Not installed

            # Call adapter uninstall
            adapter_factory = self.adapters.get(extension_id)
            try:
                if adapter_factory:
                    adapter = adapter_factory(user_ext.config or {})
                    await adapter.uninstall()
            except Exception:
                pass  # Best effort

            # Delete user extension record
            await session.delete(user_ext)
            await session.commit()

            # Fire event
            try:
                await self.events.on_extension_uninstalled(extension_id, user_id)
            except Exception:
                pass
        finally:
            await self._close_session(session)

    async def list_user_extensions(self, user_id: str) -> List[Dict[str, Any]]:
        """List extensions installed for a user."""
        session = await self._get_session()
        try:
            query = (
                select(PMUserExtension, PMExtension)
                .join(PMExtension, PMUserExtension.extension_id == PMExtension.id)
                .where(PMUserExtension.user_id == user_id)
            )
            result = await session.execute(query)
            rows = result.all()
            return [
                {
                    "extension_id": ue.extension_id,
                    "name": ext.name,
                    "description": ext.description,
                    "tool_type": ext.tool_type,
                    "status": ue.status,
                    "config": ue.config,
                    "error_message": getattr(ue, 'error_message', None),
                }
                for ue, ext in rows
            ]
        finally:
            await self._close_session(session)

    async def get_user_extension_status(
        self, extension_id: str, user_id: str
    ) -> Optional[str]:
        """Get installation status for a user's extension."""
        session = await self._get_session()
        try:
            query = select(PMUserExtension).where(
                PMUserExtension.user_id == user_id,
                PMUserExtension.extension_id == extension_id,
            )
            result = await session.execute(query)
            user_ext = result.scalar_one_or_none()
            return user_ext.status if user_ext else None
        finally:
            await self._close_session(session)
