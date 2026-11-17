import pytest
from pydantic import ValidationError
from backend.models.schemas import AgentCreateRequest, AgentRuntimeConfig, GatewayResponse, TokenUsage, AgentRead
from backend.models.constants import ResponseCode
import uuid

def test_agent_config_schema():
    # Valid
    config = AgentCreateRequest(
        name="Test assistant",
        description="Schema test",
        llm_provider_url="https://provider.example/v1",
        llm_api_key="test-placeholder-key",
        llm_model_name="gpt-3.5-turbo",
        runtime_config=AgentRuntimeConfig(temperature=0.7),
        tools=["calculator"]
    )
    assert config.name == "Test assistant"
    assert config.llm_model_name == "gpt-3.5-turbo"
    assert "calculator" in config.tools

    # AgentCreateRequest follows Pydantic's current default extra-field policy.
    # Required fields and validators are the contract; it does not forbid extras.

def test_agent_read_schema():
    agent_id = uuid.uuid4()
    agent = AgentRead(
        id=agent_id,
        name="Test",
        description="Schema test",
        llm_provider_url="https://provider.example/v1",
        llm_model_name="gpt-4",
        runtime_config=AgentRuntimeConfig(),
        capability_flags={},
        tools=[],
        constraints={},
        has_api_key=False,
    )
    assert agent.id == agent_id
    assert agent.name == "Test"

def test_gateway_response_schema():
    # Valid with token usage
    resp = GatewayResponse(
        content="Hello",
        token_usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    )
    assert resp.content == "Hello"
    assert resp.token_usage.total_tokens == 15

    # Error response
    from backend.models.schemas import GatewayError
    err_resp = GatewayResponse(
        content="",
        token_usage=TokenUsage(),
        error=GatewayError(code=ResponseCode.MODEL_ERROR, message="Model unavailable")
    )
    assert err_resp.error is not None
    assert err_resp.error.code == str(ResponseCode.MODEL_ERROR.value)

def test_response_code_constants():
    assert ResponseCode.SUCCESS == 0
    assert ResponseCode.MODEL_ERROR == 2000
    assert ResponseCode.TOOL_ERROR == 3000
