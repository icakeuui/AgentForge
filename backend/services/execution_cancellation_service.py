import asyncio
import uuid
from typing import Dict, Set


class ExecutionCancellationService:
    def __init__(self) -> None:
        self._tasks: Dict[uuid.UUID, asyncio.Task[None]] = {}
        self._cancelled_execution_ids: Set[uuid.UUID] = set()

    def register(self, execution_id: uuid.UUID, task: asyncio.Task[None]) -> None:
        self._tasks[execution_id] = task

    def unregister(self, execution_id: uuid.UUID) -> None:
        self._tasks.pop(execution_id, None)
        self.clear(execution_id)

    def request_cancel(self, execution_id: uuid.UUID) -> bool:
        self._cancelled_execution_ids.add(execution_id)
        task = self._tasks.get(execution_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def is_cancelled(self, execution_id: uuid.UUID) -> bool:
        return execution_id in self._cancelled_execution_ids

    def clear(self, execution_id: uuid.UUID) -> None:
        self._cancelled_execution_ids.discard(execution_id)


execution_cancellation_service = ExecutionCancellationService()
