import uuid

import pytest
from fastapi.testclient import TestClient

import backend.api.routes.agents as agents_routes
from backend.models.orm import Agent, AgentOwnership
from backend.services.agent_runtime_assembler import ResolvedAgentRuntime


TEST_TEAM_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _create_agent(db_session) -> uuid.UUID:
    agent_id = uuid.uuid4()
    db_session.add(
        Agent(
            id=agent_id,
            config={
                "name": "Policy Inspect Agent",
                "description": "Integration test agent",
                "llm_provider_url": "https://example.com/v1",
                "llm_api_key_encrypted": "encrypted-key",
                "llm_model_name": "gpt-4o-mini",
                "runtime_config": {"temperature": 0.0},
                "capability_flags": {"supports_tools": True},
                "tools": ["builtin.python_exec"],
                "constraints": {"max_steps": 4},
            },
        )
    )
    db_session.add(AgentOwnership(agent_id=agent_id, team_id=TEST_TEAM_ID))
    await db_session.commit()
    return agent_id


def _runtime(agent_id: uuid.UUID) -> ResolvedAgentRuntime:
    return ResolvedAgentRuntime(
        agent_id=str(agent_id),
        agent_config={"capability_flags": {"supports_tools": True}, "constraints": {"max_steps": 4}},
        supports_tools=True,
        tool_schemas=[
            {
                "type": "function",
                "function": {
                    "name": "python_exec",
                    "description": "Execute Python",
                    "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
                },
            }
        ],
        resolved_tool_names=["python_exec"],
        max_steps=4,
        tool_catalog_entries=[
            {
                "id": "builtin.python_exec",
                "openai_schema": {
                    "type": "function",
                    "function": {
                        "name": "python_exec",
                        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
                    },
                },
                "risk_level": "high",
                "side_effect": "write",
                "requires_confirmation": True,
                "allowed_intents": ["HIGH_RISK_TOOL", "TOOL_REQUIRED"],
                "domains": ["python"],
                "max_calls_per_run": 1,
            }
        ],
        bound_tool_ids=["builtin.python_exec"],
    )


@pytest.mark.asyncio
async def test_policy_inspect_reports_high_risk_confirmation(client: TestClient, db_session, monkeypatch):
    agent_id = await _create_agent(db_session)

    async def fake_resolve_agent_runtime(**kwargs):
        return _runtime(agent_id)

    monkeypatch.setattr(agents_routes.marketplace_tool_adapter, "resolve_agent_runtime", fake_resolve_agent_runtime)

    response = client.post(
        f"/agents/{agent_id}/policy/inspect",
        json={"input": "请调用 python 删除全部临时数据"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["classification"]["intent_type"] == "HIGH_RISK_TOOL"
    assert data["pre_policy"]["requires_user_confirmation"] is True
    assert data["allowed_tool_ids_for_turn"] == []
    assert data["pre_policy"]["blocked_tool_ids"][0]["tool_id"] == "builtin.python_exec"
