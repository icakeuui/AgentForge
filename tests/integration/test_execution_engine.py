import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.core.security import encrypt_api_key
from backend.models.constants import ExecutionStatus, TerminationReason
from backend.models.orm import Agent, AgentOwnership, KnowledgeDocument
from backend.models.schemas import AuthContext, ConversationHistoryMessage, GatewayResponse, GatewayToolCall, TokenUsage
from backend.services.agent_runtime_assembler import ResolvedAgentRuntime
from backend.services.execution_log_service import execution_log_service
from backend.services.knowledge_service import knowledge_service
from backend.services.langgraph_execution_strategy import LangGraphExecutionStrategy
from backend.services.tool_need_classifier import tool_need_classifier
from backend.services.retrieval_policy_service import retrieval_policy_service

TEST_TEAM_ID = "00000000-0000-0000-0000-000000000001"


def _auth_context() -> AuthContext:
    return AuthContext(
        user_id="user-integration",
        team_id=TEST_TEAM_ID,
        auth_mode="jwt",
        request_id="req-test-engine",
    )


async def _create_agent(
    db_session,
    *,
    supports_tools: bool = True,
    runtime_config: dict | None = None,
) -> uuid.UUID:
    agent_id = uuid.uuid4()
    db_session.add(
        Agent(
            id=agent_id,
            config={
                "name": "LangGraph Test Agent",
                "description": "Integration test agent",
                "llm_provider_url": "https://example.com/v1",
                "llm_api_key_encrypted": encrypt_api_key("test-key"),
                "llm_model_name": "gpt-4o-mini",
                "runtime_config": runtime_config or {"temperature": 0.0},
                "capability_flags": {"supports_tools": supports_tools},
                "constraints": {"max_steps": 4},
            },
        )
    )
    db_session.add(AgentOwnership(agent_id=agent_id, team_id=uuid.UUID(TEST_TEAM_ID)))
    await db_session.commit()
    return agent_id


async def _create_agent_with_tools(db_session, tools: list[str], *, supports_tools: bool = True) -> uuid.UUID:
    agent_id = uuid.uuid4()
    db_session.add(
        Agent(
            id=agent_id,
            config={
                "name": "LangGraph Test Agent",
                "description": "Integration test agent",
                "llm_provider_url": "https://example.com/v1",
                "llm_api_key_encrypted": encrypt_api_key("test-key"),
                "llm_model_name": "gpt-4o-mini",
                "runtime_config": {"temperature": 0.0},
                "capability_flags": {"supports_tools": supports_tools},
                "constraints": {"max_steps": 4},
                "tools": tools,
            },
        )
    )
    db_session.add(AgentOwnership(agent_id=agent_id, team_id=uuid.UUID(TEST_TEAM_ID)))
    await db_session.commit()
    return agent_id


def _tool_schema(name: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Tool schema for {name}",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def test_langgraph_strategy_truncates_injected_knowledge_context():
    long_content = "知识内容" * 1000
    results = [
        SimpleNamespace(
            document_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            title=f"资料 {index}",
            document_title=f"资料 {index}",
            source_filename=f"资料 {index}.pdf",
            content=long_content,
            document_id=uuid.uuid4(),
            chunk_id=uuid.uuid4(),
            score=1.0,
        )
        for index in range(4)
    ]

    knowledge_hits, context, original_chars, injected_chars = LangGraphExecutionStrategy._truncate_knowledge_context_items(results)

    assert len(context) < original_chars
    assert injected_chars <= LangGraphExecutionStrategy.MAX_KNOWLEDGE_CONTEXT_CHARS
    assert len(knowledge_hits) == 4
    assert all(hit["truncated"] for hit in knowledge_hits)
    assert all(f"source_filename: 资料 {index}.pdf" in context for index in range(4))
    assert all(hit["source_filename"] == f"资料 {index}.pdf" for index, hit in enumerate(knowledge_hits))


def test_document_inventory_questions_use_structured_retrieval_policy():
    classification = tool_need_classifier.classify("你的知识库里面都有什么文件")

    assert classification.intent_type == "KB_REQUIRED"
    assert classification.query_subtype == "document_inventory"
    policy = retrieval_policy_service.resolve(classification)
    assert policy.retrieval_mode == "document_inventory"
    assert policy.required is True


def test_multi_source_question_detection_is_narrow():
    assert LangGraphExecutionStrategy._is_multi_source_question("请对比国家目录和辽宁省目录")
    assert LangGraphExecutionStrategy._is_multi_source_question("综合多个文件回答这个问题")
    assert not LangGraphExecutionStrategy._is_multi_source_question("国家竞赛目录里有哪些竞赛？")


@pytest.mark.asyncio
async def test_document_inventory_uses_complete_metadata_in_llm_context(db_session):
    agent_id = await _create_agent(db_session, supports_tools=False)
    document_sources = [
        ("国家竞赛目录.pdf", "国家竞赛目录.pdf"),
        ("辽宁省竞赛目录.pdf", "辽宁省竞赛目录.pdf"),
        ("学校竞赛认定目录.pdf", "学校竞赛认定目录（2026版）"),
    ]
    for filename, title in document_sources:
        db_session.add(KnowledgeDocument(
            agent_id=agent_id,
            team_id=uuid.UUID(TEST_TEAM_ID),
            title=title,
            source_filename=filename,
            document_type="pdf",
            content="test-only metadata inventory fixture",
            status="ACTIVE",
            chunk_count=3,
        ))
    await db_session.commit()

    model_gateway = AsyncMock()
    model_gateway.call.return_value = GatewayResponse(
        content="已列出关联资料。", token_usage=TokenUsage(total_tokens=5), finish_reason="stop"
    )
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, [], supports_tools=False)
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="你的知识库里面都有什么文件？",
        auth_context=_auth_context(),
        request_id="req-document-inventory",
    )

    system_prompt = model_gateway.call.await_args.kwargs["messages"][0].content
    assert result.status == ExecutionStatus.SUCCEEDED
    assert "COMPLETE DOCUMENT INVENTORY: 3 linked document records" in system_prompt
    for filename, _title in document_sources:
        assert filename in system_prompt
    assert "source_filename:" in system_prompt
    assert "chunk_id:" not in system_prompt


def _resolved_runtime(
    agent_id: uuid.UUID,
    tool_schemas: list[dict],
    *,
    supports_tools: bool = True,
    configured_tools: list[str] | None = None,
    unresolved_tools: list[str] | None = None,
    requested_tool_names: list[str] | None = None,
    unavailable_requested_tools: list[str] | None = None,
    binding_drift: dict | None = None,
    resolution_source: str = "bindings",
    max_steps: int = 4,
) -> ResolvedAgentRuntime:
    tool_names = [
        str(((tool.get("function") or {}).get("name", ""))).strip()
        for tool in tool_schemas
        if isinstance(tool, dict)
    ]
    return ResolvedAgentRuntime(
        agent_id=str(agent_id),
        agent_config={
            "capability_flags": {"supports_tools": supports_tools},
            "constraints": {"max_steps": max_steps},
            "tools": configured_tools or [],
        },
        supports_tools=supports_tools,
        tool_schemas=tool_schemas,
        resolved_tool_names=tool_names,
        max_steps=max_steps,
        unresolved_tools=unresolved_tools or [],
        configured_tools=configured_tools or [],
        bound_tool_ids=tool_names,
        requested_tool_names=requested_tool_names or [],
        unavailable_requested_tools=unavailable_requested_tools or [],
        binding_drift=binding_drift or {},
        resolution_source=resolution_source,
    )


@pytest.mark.asyncio
async def test_langgraph_strategy_includes_conversation_history_in_model_messages(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, [])
    model_gateway.call.return_value = GatewayResponse(
        content="我记得你叫老孙。",
        token_usage=TokenUsage(total_tokens=6),
        finish_reason="stop",
    )
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="我刚才说我叫什么？",
        auth_context=_auth_context(),
        request_id="req-conversation-history",
        conversation_history=[
            ConversationHistoryMessage(role="user", content="我叫老孙。"),
            ConversationHistoryMessage(role="assistant", content="好的，我记住了。"),
        ],
    )

    first_call_kwargs = model_gateway.call.await_args.kwargs
    messages = first_call_kwargs["messages"]
    assert result.status == ExecutionStatus.SUCCEEDED
    assert [message.role for message in messages] == ["system", "user", "assistant", "user"]
    assert "Agent Persona And Logic (System Prompt)" in (messages[0].content or "")
    assert "Integration test agent" in (messages[0].content or "")
    assert [message.content for message in messages[1:]] == [
        "我叫老孙。",
        "好的，我记住了。",
        "我刚才说我叫什么？",
    ]


@pytest.mark.asyncio
async def test_langgraph_strategy_continues_length_limited_model_output(db_session):
    agent_id = await _create_agent(db_session)
    chunks = [
        "第一段说明内容。" * 25,
        "第二段分析内容。" * 25,
        "第三段补充内容。" * 25,
        "第四段总结内容。" * 25,
        "第五段最终结论。" * 25,
    ]
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, [], max_steps=1)
    model_gateway.call.side_effect = [
        *[
            GatewayResponse(content=chunk, token_usage=TokenUsage(total_tokens=10), finish_reason="length")
            for chunk in chunks[:-1]
        ],
        GatewayResponse(content=chunks[-1], token_usage=TokenUsage(total_tokens=8), finish_reason="stop"),
    ]
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="请完成一个较长的分析任务。",
        auth_context=_auth_context(),
        request_id="req-output-continuation",
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.termination_reason == TerminationReason.SUCCESS
    assert result.final_answer == "".join(chunks)
    assert 1000 <= len(result.final_answer) <= 2000
    assert model_gateway.call.await_count == 5
    continuation_messages = model_gateway.call.await_args_list[1].kwargs["messages"]
    assert any(message.role == "assistant" and message.content == chunks[0] for message in continuation_messages)
    assert any(message.role == "user" and "同一条回答的续写" in message.content for message in continuation_messages)


@pytest.mark.asyncio
async def test_langgraph_strategy_continues_beyond_previous_twenty_call_limit(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, [], max_steps=1)
    continuation_count = 23
    model_gateway.call.side_effect = [
        *[
            GatewayResponse(content=f"分段内容 {index}。", token_usage=TokenUsage(total_tokens=10), finish_reason="length")
            for index in range(continuation_count)
        ],
        GatewayResponse(content="最终完成。", token_usage=TokenUsage(total_tokens=8), finish_reason="stop"),
    ]
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="请生成较长内容并自动续写。",
        auth_context=_auth_context(),
        request_id="req-unbounded-continuation",
    )

    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.termination_reason == TerminationReason.SUCCESS
    assert result.final_answer == "".join(f"分段内容 {index}。" for index in range(continuation_count)) + "最终完成。"
    assert model_gateway.call.await_count == continuation_count + 1


@pytest.mark.asyncio
async def test_langgraph_strategy_stops_repeated_continuation_loop(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, [], max_steps=1)
    model_gateway.call.side_effect = [
        GatewayResponse(content="重复片段内容。", token_usage=TokenUsage(total_tokens=10), finish_reason="length"),
        GatewayResponse(content="重复片段内容。", token_usage=TokenUsage(total_tokens=10), finish_reason="length"),
    ]
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="请继续生成。",
        auth_context=_auth_context(),
        request_id="req-continuation-stalled",
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.termination_reason == TerminationReason.CONTINUATION_STALLED
    assert "重复了先前片段" in (result.final_answer or "")
    assert model_gateway.call.await_count == 2


@pytest.mark.asyncio
async def test_langgraph_strategy_trims_old_history_before_model_call(db_session):
    agent_id = await _create_agent(
        db_session,
        runtime_config={"temperature": 0.0, "context_window": 1200, "reserved_completion_tokens": 64},
    )
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, [])
    model_gateway.call.return_value = GatewayResponse(
        content="收到最新问题。",
        token_usage=TokenUsage(total_tokens=6),
        finish_reason="stop",
    )
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="请回答最新问题。",
        auth_context=_auth_context(),
        request_id="req-context-budget-trim",
        conversation_history=[
            ConversationHistoryMessage(role="user", content="旧问题 " * 900),
            ConversationHistoryMessage(role="assistant", content="旧回答 " * 900),
        ],
    )

    first_call_kwargs = model_gateway.call.await_args.kwargs
    messages = first_call_kwargs["messages"]
    assert result.status == ExecutionStatus.SUCCEEDED
    assert [message.role for message in messages] == ["system", "user"]
    assert messages[-1].content == "请回答最新问题。"


@pytest.mark.asyncio
async def test_langgraph_strategy_logs_context_budget_but_still_calls_model(db_session):
    agent_id = await _create_agent(
        db_session,
        runtime_config={"temperature": 0.0, "context_window": 300, "reserved_completion_tokens": 64},
    )
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, [])
    model_gateway.call.return_value = GatewayResponse(
        content="收到最新问题。",
        token_usage=TokenUsage(total_tokens=6),
        finish_reason="stop",
    )
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="最新问题 " * 1000,
        auth_context=_auth_context(),
        request_id="req-context-budget-exceeded",
    )

    first_call_kwargs = model_gateway.call.await_args.kwargs
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.termination_reason == TerminationReason.SUCCESS
    assert first_call_kwargs["messages"][-1].content == "最新问题 " * 1000


@pytest.mark.asyncio
async def test_langgraph_strategy_injects_retrieved_knowledge_into_system_prompt(db_session):
    agent_id = await _create_agent(db_session)
    await knowledge_service.create_document(
        db_session,
        agent_id=agent_id,
        team_id=uuid.UUID(TEST_TEAM_ID),
        title="计费规则",
        content="企业版套餐支持每月 10000 次自动化执行，超出后需要购买额外额度。",
    )
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, [])
    model_gateway.call.return_value = GatewayResponse(
        content="企业版套餐每月支持 10000 次自动化执行。",
        token_usage=TokenUsage(total_tokens=8),
        finish_reason="stop",
    )
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="企业版每月有多少次自动化执行？",
        auth_context=_auth_context(),
        request_id="req-knowledge-context",
    )

    first_call_kwargs = model_gateway.call.await_args.kwargs
    system_content = first_call_kwargs["messages"][0].content or ""
    assert result.status == ExecutionStatus.SUCCEEDED
    assert "Retrieved Knowledge" in system_content
    assert "企业版套餐支持每月 10000 次自动化执行" in system_content


@pytest.mark.asyncio
async def test_knowledge_search_matches_short_chinese_possession_question(db_session):
    agent_id = await _create_agent(db_session)
    await knowledge_service.create_document(
        db_session,
        agent_id=agent_id,
        team_id=uuid.UUID(TEST_TEAM_ID),
        title="用户资产",
        content="我有一个大房子和五辆车。",
    )

    results = await knowledge_service.search(
        db_session,
        agent_id=agent_id,
        team_id=uuid.UUID(TEST_TEAM_ID),
        query="我有什么？",
        limit=5,
    )

    assert results
    assert results[0].title == "用户资产"


@pytest.mark.asyncio
async def test_langgraph_strategy_runs_python_add_tool_and_persists_react_steps(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_schemas = [
        _tool_schema(
            "python_add_tool",
            {"a": {"type": "integer"}, "b": {"type": "integer"}},
            ["a", "b"],
        )
    ]
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, tool_schemas)
    tool_runtime.execute_tool.return_value = json.dumps({"result": 5})
    model_gateway.call.side_effect = [
        GatewayResponse(
            content="必须调用 python_add_tool 计算结果。",
            token_usage=TokenUsage(total_tokens=11),
            finish_reason="tool_calls",
            tool_calls=[
                GatewayToolCall(
                    id="call-python-add",
                    function_name="python_add_tool",
                    function_arguments='{"a":2,"b":3}',
                )
            ],
        ),
        GatewayResponse(
            content="python_add_tool 已返回 5，所以最终答案是 5。",
            token_usage=TokenUsage(total_tokens=7),
            finish_reason="stop",
        ),
    ]
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="必须调用 python_add_tool 计算 2+3，不允许直接心算。",
        auth_context=_auth_context(),
        request_id="req-python-add",
    )

    replay = await execution_log_service.get_execution_replay(result.execution_id, team_id=uuid.UUID(TEST_TEAM_ID))
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.termination_reason == TerminationReason.SUCCESS
    assert "5" in (result.final_answer or "")
    assert replay is not None
    assert replay["react_steps"][0]["action"]["tool_id"] == "python_add_tool"
    assert replay["react_steps"][0]["observation"]["ok"] is True
    assert replay["react_steps"][0]["observation"]["result"] == {"result": 5}


@pytest.mark.asyncio
async def test_langgraph_strategy_runs_echo_tool_with_real_replay(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_schemas = [
        _tool_schema("echo_tool", {"text": {"type": "string"}}, ["text"])
    ]
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, tool_schemas)
    tool_runtime.execute_tool.return_value = json.dumps({"echo": "hello-agent"})
    model_gateway.call.side_effect = [
        GatewayResponse(
            content="先调用 echo_tool。",
            token_usage=TokenUsage(total_tokens=8),
            finish_reason="tool_calls",
            tool_calls=[
                GatewayToolCall(
                    id="call-echo",
                    function_name="echo_tool",
                    function_arguments='{"text":"hello-agent"}',
                )
            ],
        ),
        GatewayResponse(
            content="echo_tool 输出为 hello-agent。",
            token_usage=TokenUsage(total_tokens=5),
            finish_reason="stop",
        ),
    ]
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="调用 echo_tool 输出 hello-agent。",
        auth_context=_auth_context(),
        request_id="req-echo",
    )

    replay = await execution_log_service.get_execution_replay(result.execution_id, team_id=uuid.UUID(TEST_TEAM_ID))
    assert result.status == ExecutionStatus.SUCCEEDED
    assert replay is not None
    assert replay["react_steps"][0]["action"]["tool_id"] == "echo_tool"
    assert replay["react_steps"][0]["observation"]["result"] == {"echo": "hello-agent"}


@pytest.mark.asyncio
async def test_langgraph_strategy_turns_tool_failure_into_observation(db_session):
    agent_id = await _create_agent(db_session)
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_schemas = [
        _tool_schema("python_add_tool", {"a": {"type": "integer"}, "b": {"type": "integer"}}, ["a", "b"])
    ]
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(agent_id, tool_schemas)
    tool_runtime.execute_tool.side_effect = RuntimeError("invalid parameters for python_add_tool")
    model_gateway.call.side_effect = [
        GatewayResponse(
            content="先尝试工具。",
            token_usage=TokenUsage(total_tokens=9),
            finish_reason="tool_calls",
            tool_calls=[
                GatewayToolCall(
                    id="call-bad-python-add",
                    function_name="python_add_tool",
                    function_arguments='{"a":"bad","b":3}',
                )
            ],
        ),
        GatewayResponse(
            content="工具执行失败，参数不合法。",
            token_usage=TokenUsage(total_tokens=4),
            finish_reason="stop",
        ),
    ]
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="故意传非法参数，让工具失败。",
        auth_context=_auth_context(),
        request_id="req-tool-failure",
    )

    replay = await execution_log_service.get_execution_replay(result.execution_id, team_id=uuid.UUID(TEST_TEAM_ID))
    assert result.status == ExecutionStatus.SUCCEEDED
    assert replay is not None
    assert replay["react_steps"][0]["observation"]["ok"] is False
    assert replay["react_steps"][0]["observation"]["error"]["message"] == "invalid parameters for python_add_tool"


@pytest.mark.asyncio
async def test_langgraph_strategy_lets_model_choose_named_tool_structurally(db_session):
    agent_id = await _create_agent_with_tools(db_session, ["python_executor"])
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_schemas = [_tool_schema("builtin/python_executor", {"code": {"type": "string"}}, ["code"])]
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(
        agent_id,
        tool_schemas,
        configured_tools=["python_executor"],
        requested_tool_names=["builtin/python_executor"],
    )
    tool_runtime.execute_tool.return_value = json.dumps({"sum": 15, "max": 5})
    model_gateway.call.side_effect = [
        GatewayResponse(
            content="需要执行 python_executor。",
            token_usage=TokenUsage(total_tokens=10),
            finish_reason="tool_calls",
            tool_calls=[
                GatewayToolCall(
                    id="call-python-executor",
                    function_name="builtin/python_executor",
                    function_arguments='{"code":"result = {\\"sum\\": sum([1,2,3,4,5]), \\"max\\": max([1,2,3,4,5])}"}',
                )
            ],
        ),
        GatewayResponse(
            content="结果为 sum=15, max=5。",
            token_usage=TokenUsage(total_tokens=6),
            finish_reason="stop",
        ),
    ]
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input='请调用 python_executor 执行以下代码并返回结果：result = {"sum": sum([1,2,3,4,5]), "max": max([1,2,3,4,5])}',
        auth_context=_auth_context(),
        request_id="req-python-executor",
    )

    first_call_kwargs = model_gateway.call.await_args_list[0].kwargs
    replay = await execution_log_service.get_execution_replay(result.execution_id, team_id=uuid.UUID(TEST_TEAM_ID))
    assert first_call_kwargs["tool_choice"] is None
    assert result.status == ExecutionStatus.SUCCEEDED
    assert replay is not None
    assert replay["react_steps"][0]["action"]["tool_id"] == "builtin/python_executor"
    assert replay["react_steps"][0]["observation"]["result"] == {"sum": 15, "max": 5}


@pytest.mark.asyncio
async def test_langgraph_strategy_fails_when_requested_tool_is_unavailable(db_session):
    agent_id = await _create_agent_with_tools(db_session, ["python_executor"])
    model_gateway = AsyncMock()
    tool_runtime = AsyncMock()
    tool_runtime.resolve_agent_runtime.return_value = _resolved_runtime(
        agent_id,
        [],
        configured_tools=["python_executor"],
        requested_tool_names=["builtin/python_executor"],
        unavailable_requested_tools=["builtin/python_executor"],
        binding_drift={"config_only": ["builtin/python_executor"]},
        resolution_source="binding_drift",
    )
    strategy = LangGraphExecutionStrategy(
        model_gateway=model_gateway,
        tool_runtime=tool_runtime,
        execution_log_service=execution_log_service,
    )

    result = await strategy.run(
        agent_id=str(agent_id),
        user_input="请调用 python_executor 计算 1+1。",
        auth_context=_auth_context(),
        request_id="req-missing-runtime-tool",
    )

    assert result.status == ExecutionStatus.FAILED
    assert "未绑定这些工具" in (result.final_answer or "")
    model_gateway.call.assert_not_called()
