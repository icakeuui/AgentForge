import uuid
from typing import List, Optional

from backend.core.logging import set_auth_mode, set_request_id, set_team_id, set_user_id
from backend.models.schemas import AuthContext, ConversationHistoryMessage, ExecutionResult
from backend.services.execution_log_service import execution_log_service
from backend.services.langgraph_execution_strategy import LangGraphExecutionStrategy
from backend.services.marketplace_tool_adapter import marketplace_tool_adapter
from backend.services.model_gateway import model_gateway


class ExecutionEngine:
    def __init__(self) -> None:
        self.strategy = LangGraphExecutionStrategy(
            model_gateway=model_gateway,
            tool_runtime=marketplace_tool_adapter,
            execution_log_service=execution_log_service,
        )

    async def run(
        self,
        agent_id: str,
        user_input: str,
        auth_context: AuthContext,
        request_id: Optional[str] = None,
        conversation_history: Optional[List[ConversationHistoryMessage]] = None,
        confirmed_tool_actions: Optional[list[dict]] = None,
        policy_overrides: Optional[dict] = None,
        execution_id: Optional[uuid.UUID] = None,
        start_log: bool = True,
    ) -> ExecutionResult:
        if not request_id:
            request_id = auth_context.request_id or f"exec-{uuid.uuid4().hex[:8]}"

        set_request_id(request_id)
        set_team_id(auth_context.team_id)
        set_user_id(auth_context.user_id)
        set_auth_mode(auth_context.auth_mode)

        return await self.strategy.run(
            agent_id=agent_id,
            user_input=user_input,
            auth_context=auth_context,
            request_id=request_id,
            conversation_history=conversation_history,
            confirmed_tool_actions=confirmed_tool_actions,
            policy_overrides=policy_overrides,
            execution_id=execution_id,
            start_log=start_log,
        )


execution_engine = ExecutionEngine()
