import pytest
from pydantic import ValidationError
from backend.models.schemas import AgentConfig, ModelConfig, GatewayResponse, TokenUsage, AgentRead
from backend.models.constants import ResponseCode
import uuid

def test_agent_config_schema():
    # Valid
    config = AgentConfig(
        system_prompt="You are an assistant.",
        model_config=ModelConfig(model="gpt-3.5-turbo", temperature=0.7),
        tools=["calculator"]
    )
    assert config.system_prompt == "You are an assistant."
    assert config.llm_config.model == "gpt-3.5-turbo"
    assert "calculator" in config.tools

    # Invalid: extra fields forbidden
    with pytest.raises(ValidationError):
        AgentConfig(
            system_prompt="Test",
            model_config=ModelConfig(model="gpt-4", temperature=0),
            tools=[],
            extra_field="not allowed"
        )

def test_agent_read_schema():
    agent_id = uuid.uuid4()
    agent = AgentRead(
        id=agent_id,
        system_prompt="Test",
        model_config=ModelConfig(model="gpt-4"),
        tools=[]
    )
    assert agent.id == agent_id
    assert agent.system_prompt == "Test"

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
    assert err_resp.error.code == ResponseCode.MODEL_ERROR

def test_response_code_constants():
    assert ResponseCode.SUCCESS == 0
    assert ResponseCode.MODEL_ERROR == 2000
    assert ResponseCode.TOOL_ERROR == 3000
