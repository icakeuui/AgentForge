import uuid
from typing import Any, Dict, List, Optional

from backend.core.config import settings
from backend.core.database import AsyncSessionLocal
from backend.core.exceptions import ValidationException
from backend.services.agent_runtime_assembler import AgentRuntimeAssembler, ResolvedAgentRuntime
from plugin_marketplace import MarketplaceAPI
from plugin_marketplace.exceptions import ToolBindingValidationError


class MarketplaceToolAdapter:
    """
    Adapter that enforces tool access through plugin marketplace only.
    """

    def __init__(self, marketplace_api: Optional[MarketplaceAPI] = None):
        self._marketplace_api = marketplace_api
        self._runtime_assembler = AgentRuntimeAssembler(self)

    async def _get_api(self) -> MarketplaceAPI:
        if self._marketplace_api is None:
            self._marketplace_api = MarketplaceAPI(
                database_url=settings.DB_URL,
                session_factory=AsyncSessionLocal,
            )
            await self._marketplace_api.initialize()
        return self._marketplace_api

    async def get_tools_schema(self, agent_id: uuid.UUID) -> List[Dict[str, Any]]:
        api = await self._get_api()
        tools = await api.get_tools_for_agent(str(agent_id))
        return tools or []

    async def get_all_tools_schema(self) -> List[Dict[str, Any]]:
        api = await self._get_api()
        tools = await api.get_tool_schemas()
        return tools or []

    async def sync_agent_tools(self, agent_id: str, tool_ids: List[str]) -> None:
        api = await self._get_api()
        try:
            return await api.replace_agent_tools(agent_id, tool_ids)
        except ToolBindingValidationError as exc:
            raise ValidationException(
                f"Invalid tool ids: {', '.join(exc.missing_tool_ids)}"
            ) from exc

    async def validate_tool_ids(self, tool_ids: List[str]) -> Any:
        api = await self._get_api()
        return await api.validate_tool_ids(tool_ids)

    async def get_agent_tool_ids(self, agent_id: str) -> List[str]:
        api = await self._get_api()
        return await api.get_agent_tool_ids(agent_id)

    async def get_tool_catalog_entries(self, tool_ids: List[str]) -> List[Dict[str, Any]]:
        api = await self._get_api()
        return await api.get_tool_catalog_entries(tool_ids)

    async def resolve_agent_runtime(
        self,
        agent_id: str,
        agent_config: Dict[str, Any],
        user_input: str,
    ) -> ResolvedAgentRuntime:
        return await self._runtime_assembler.assemble(
            agent_id=agent_id,
            agent_config=agent_config,
            user_input=user_input,
        )

    async def apply_default_agent_tools(self, agent_id: str, tool_ids: List[str]) -> Any:
        return await self.sync_agent_tools(agent_id, tool_ids)

    async def execute_tool(
        self,
        tool_id: str,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        api = await self._get_api()
        return await api.execute_tool(tool_id=tool_id, arguments=arguments, context=context)


marketplace_tool_adapter = MarketplaceToolAdapter()
