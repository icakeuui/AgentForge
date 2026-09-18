import uuid

import pytest

from backend.models.constants import ExecutionState, TerminationReason
from backend.services.execution_log_service import execution_log_service

TEST_TEAM_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.asyncio
async def test_execution_logs_lifecycle(db_session):
    execution_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    request_id = str(uuid.uuid4())

    await execution_log_service.start_execution(
        execution_id=execution_id,
        request_id=request_id,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
    )
    await execution_log_service.append_react_step(
        execution_id=execution_id,
        request_id=request_id,
        step_index=1,
        state_before=ExecutionState.ACTING.value,
        state_after=ExecutionState.OBSERVING.value,
        thought="Need calculator output",
        action={"type": "tool_call", "tool_id": "calculator", "arguments": {"exp": "1+1"}},
        observation={"ok": True, "result": {"value": 2}, "error": None},
        step_status="success",
    )
    await execution_log_service.complete_execution(
        execution_id=execution_id,
        final_state=ExecutionState.FINISHED.value,
        termination_reason=TerminationReason.SUCCESS.value,
        steps_used=1,
        status="SUCCEEDED",
        final_answer="The answer is 2.",
    )

    log_data = await execution_log_service.get_execution_replay(execution_id, TEST_TEAM_ID)
    assert log_data is not None
    assert log_data["execution_id"] == str(execution_id)
    assert log_data["status"] == "SUCCEEDED"
    assert len(log_data["react_steps"]) == 1
    step = log_data["react_steps"][0]
    assert step["step_index"] == 1
    assert step["thought"] == "Need calculator output"
    assert step["action"]["tool_id"] == "calculator"
    assert step["observation"]["result"] == {"value": 2}


@pytest.mark.asyncio
async def test_execution_logs_team_isolation(db_session):
    execution_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    request_id = str(uuid.uuid4())

    await execution_log_service.start_execution(
        execution_id=execution_id,
        request_id=request_id,
        agent_id=agent_id,
        team_id=TEST_TEAM_ID,
    )

    log_data = await execution_log_service.get_execution_replay(execution_id, uuid.uuid4())
    assert log_data is None
