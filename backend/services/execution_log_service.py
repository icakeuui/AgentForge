import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from sqlalchemy import select, update
from backend.core.database import AsyncSessionLocal
from backend.models.orm import ExecutionLog, ReactStepLog
from backend.models.schemas import ReactStep, TokenUsage, ExecutionErrorModel
from backend.models.schemas import ExecutionStepLogContract
from backend.core.logging import logger

class ExecutionLogService:
    async def start_execution(
        self,
        execution_id: uuid.UUID,
        agent_id: uuid.UUID,
        team_id: uuid.UUID,
        request_id: str,
        initial_state: str = "INIT",
        input_data: str = ""
    ) -> None:
        async with AsyncSessionLocal() as session:
            log = ExecutionLog(
                execution_id=execution_id,
                agent_id=agent_id,
                team_id=team_id,
                request_id=request_id,
                status="PENDING",
                final_state=initial_state,
                termination_reason="",
                steps_used=0,
                started_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                data={"input_data": input_data}
            )
            session.add(log)
            await session.commit()
            logger.info(f"Execution log started: {execution_id}")

    async def start_step(
        self,
        execution_id: uuid.UUID,
        step_index: int,
        request_id: str,
        state_before: str
    ) -> Optional[int]:
        async with AsyncSessionLocal() as session:
            step_log = ReactStepLog(
                execution_id=execution_id,
                step_index=step_index,
                request_id=request_id,
                step_status="running",
                state_before=state_before
            )
            session.add(step_log)
            await session.flush()
            step_id = step_log.id
            stmt = (
                update(ExecutionLog)
                .where(ExecutionLog.execution_id == execution_id)
                .values(
                    steps_used=step_index,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt)
            await session.commit()
            return step_id

    async def complete_step(
        self,
        step_log_id: Optional[int],
        step: ReactStep,
        execution_id: uuid.UUID
    ) -> None:
        if step_log_id is None:
            return
        async with AsyncSessionLocal() as session:
            error_code = step.error.error_code if step.error else None
            error_source = step.error.error_source if step.error else None
            error_message = step.error.error_message if step.error else None
            step_status = "failed" if error_code else "success"
            stmt = (
                update(ReactStepLog)
                .where(ReactStepLog.id == step_log_id)
                .values(
                    step_status=step_status,
                    state_before=step.state_before.value,
                    state_after=step.state_after.value,
                    thought=step.thought,
                    action=step.action.model_dump(),
                    observation=step.observation.model_dump(),
                    error_code=error_code,
                    error_source=error_source,
                    error_message=error_message,
                    completed_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt)
            stmt_exec = (
                update(ExecutionLog)
                .where(ExecutionLog.execution_id == execution_id)
                .values(
                    final_state=step.state_after.value,
                    updated_at=datetime.now(timezone.utc)
                )
            )
            await session.execute(stmt_exec)
            await session.commit()

    async def complete_execution(
        self,
        execution_id: uuid.UUID,
        status: str,
        final_state: str,
        termination_reason: str,
        steps_used: int,
        final_answer: Optional[str] = None,
        total_token_usage: Optional[TokenUsage] = None,
        error: Optional[ExecutionErrorModel] = None,
        error_details: Optional[Dict[str, Any]] = None,
        step_logs: Optional[List[ExecutionStepLogContract]] = None,
    ) -> None:
        async with AsyncSessionLocal() as session:
            stmt_get = select(ExecutionLog.data).where(ExecutionLog.execution_id == execution_id)
            result = await session.execute(stmt_get)
            existing_data = result.scalar_one_or_none() or {}
            
            if total_token_usage:
                existing_data["token_usage"] = total_token_usage.model_dump()
            
            error_code = error.error_code if error else None
            error_source = error.error_source if error else None
            error_message = error.error_message if error else None
            existing_data["error_code"] = error_code
            existing_data["error_source"] = error_source
            existing_data["error_details"] = error_details
            if step_logs is not None:
                existing_data["step_logs"] = [item.model_dump() for item in step_logs]
            stmt = (
                update(ExecutionLog)
                .where(ExecutionLog.execution_id == execution_id)
                .values(
                    status=status,
                    final_state=final_state,
                    termination_reason=termination_reason,
                    steps_used=steps_used,
                    final_answer=final_answer,
                    error_code=error_code,
                    error_source=error_source,
                    error_message=error_message,
                    completed_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    data=existing_data
                )
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Execution log completed: {execution_id} | Status: {status}")

    async def terminate_if_active(
        self,
        execution_id: uuid.UUID,
        *,
        final_answer: str,
        termination_reason: str,
        team_id: Optional[uuid.UUID] = None,
    ) -> bool:
        async with AsyncSessionLocal() as session:
            stmt_get = select(ExecutionLog).where(ExecutionLog.execution_id == execution_id)
            if team_id:
                stmt_get = stmt_get.where(ExecutionLog.team_id == team_id)
            result = await session.execute(stmt_get)
            execution = result.scalar_one_or_none()
            if execution is None or execution.status not in {"PENDING", "RUNNING"}:
                return False

            existing_data = execution.data or {}
            existing_data["error_code"] = None
            existing_data["error_source"] = None
            existing_data["error_details"] = None
            stmt = (
                update(ExecutionLog)
                .where(ExecutionLog.execution_id == execution_id)
                .values(
                    status="TERMINATED",
                    final_state="TERMINATED",
                    termination_reason=termination_reason,
                    final_answer=final_answer,
                    error_code=None,
                    error_source=None,
                    error_message=None,
                    completed_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    data=existing_data,
                )
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Execution log stopped by user: {execution_id}")
            return True

    async def update_streaming_answer(
        self,
        execution_id: uuid.UUID,
        content: str,
    ) -> None:
        async with AsyncSessionLocal() as session:
            stmt_get = select(ExecutionLog.data).where(ExecutionLog.execution_id == execution_id)
            result = await session.execute(stmt_get)
            existing_data = result.scalar_one_or_none() or {}
            existing_data["streaming_answer"] = content
            stmt = (
                update(ExecutionLog)
                .where(ExecutionLog.execution_id == execution_id)
                .values(
                    status="RUNNING",
                    final_answer=content,
                    updated_at=datetime.now(timezone.utc),
                    data=existing_data,
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def append_react_step(
        self,
        execution_id: uuid.UUID,
        request_id: str,
        step_index: int,
        state_before: str,
        state_after: str,
        thought: Optional[str],
        action: Optional[Dict[str, Any]],
        observation: Optional[Dict[str, Any]],
        step_status: str,
        error_code: Optional[str] = None,
        error_source: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        async with AsyncSessionLocal() as session:
            session.add(
                ReactStepLog(
                    execution_id=execution_id,
                    step_index=step_index,
                    request_id=request_id,
                    step_status=step_status,
                    state_before=state_before,
                    state_after=state_after,
                    thought=thought,
                    action=action,
                    observation=observation,
                    error_code=error_code,
                    error_source=error_source,
                    error_message=error_message,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await session.execute(
                update(ExecutionLog)
                .where(ExecutionLog.execution_id == execution_id)
                .values(
                    status="RUNNING",
                    final_state=state_after,
                    steps_used=step_index,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def get_execution_record(self, execution_id: uuid.UUID, team_id: Optional[uuid.UUID] = None) -> Optional[ExecutionLog]:
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ExecutionLog).where(ExecutionLog.execution_id == execution_id)
                if team_id:
                    stmt = stmt.where(ExecutionLog.team_id == team_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get execution record for {execution_id}: {str(e)}")
            return None

    async def get_execution_steps(self, execution_id: uuid.UUID) -> List[ReactStepLog]:
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ReactStepLog).where(ReactStepLog.execution_id == execution_id).order_by(ReactStepLog.step_index)
                result = await session.execute(stmt)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Failed to get execution steps for {execution_id}: {str(e)}")
            return []

    async def get_execution_replay(self, execution_id: uuid.UUID, team_id: Optional[uuid.UUID] = None) -> Optional[dict]:
        execution = await self.get_execution_record(execution_id, team_id=team_id)
        if execution is None:
            return None
        steps = await self.get_execution_steps(execution_id)
        token_usage = (execution.data or {}).get("token_usage", {})
        return {
            "execution_id": str(execution.execution_id),
            "request_id": execution.request_id,
            "agent_id": str(execution.agent_id),
            "status": execution.status,
            "final_state": execution.final_state,
            "termination_reason": execution.termination_reason,
            "steps_used": execution.steps_used,
            "final_answer": execution.final_answer,
            "error_code": execution.error_code,
            "error_source": execution.error_source,
            "error_message": execution.error_message,
            "error_details": (execution.data or {}).get("error_details"),
            "error": (
                {
                    "code": execution.error_code,
                    "message": execution.error_message,
                }
                if execution.error_code
                else None
            ),
            "total_token_usage": token_usage.get("total_tokens"),
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "updated_at": execution.updated_at.isoformat() if execution.updated_at else None,
            "data": execution.data,
            "step_logs": (execution.data or {}).get("step_logs", []),
            "react_steps": [
                {
                    "step_index": s.step_index,
                    "step_status": s.step_status,
                    "state_before": s.state_before,
                    "state_after": s.state_after,
                    "thought": s.thought,
                    "action": s.action,
                    "observation": s.observation,
                    "error_code": s.error_code,
                    "error_source": s.error_source,
                    "error_message": s.error_message,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in steps
            ]
        }

# Singleton instance
execution_log_service = ExecutionLogService()
