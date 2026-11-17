from backend.models.schemas import Message
from backend.services.context_budget_manager import ContextBudgetManager


def test_context_budget_manager_drops_old_history_before_latest_user():
    manager = ContextBudgetManager()
    messages = [
        Message(role="system", content="system"),
        Message(role="user", content="old user " * 400),
        Message(role="assistant", content="old assistant " * 400),
        Message(role="user", content="latest request"),
    ]

    result = manager.fit(
        messages=messages,
        tools=[],
        model_name="unknown-local-model",
        max_completion_tokens=64,
        runtime_config={"context_window": 700, "reserved_completion_tokens": 64},
    )

    assert result.exceeded is False
    assert result.report.dropped_messages_count == 2
    assert [message.content for message in result.messages] == ["system", "latest request"]
    assert result.report.budget_status == "trimmed"


def test_context_budget_manager_truncates_large_tool_observation():
    manager = ContextBudgetManager()
    messages = [
        Message(role="system", content="system"),
        Message(role="user", content="run tool"),
        Message(role="assistant", content="", tool_calls=[]),
        Message(role="tool", tool_call_id="call-1", name="tool", content="x" * 9000),
    ]

    result = manager.fit(
        messages=messages,
        tools=[],
        model_name="gpt-4o-mini",
        max_completion_tokens=64,
        runtime_config={},
    )

    assert result.exceeded is False
    assert result.report.truncated_tool_observations_count == 1
    tool_message = result.messages[-1]
    assert tool_message.role == "tool"
    assert "content_preview" in (tool_message.content or "")
    assert "original_chars" in (tool_message.content or "")


def test_context_budget_manager_marks_exceeded_when_required_context_cannot_fit():
    manager = ContextBudgetManager()
    messages = [
        Message(role="system", content="system " * 200),
        Message(role="user", content="latest request " * 200),
    ]

    result = manager.fit(
        messages=messages,
        tools=[],
        model_name="unknown-local-model",
        max_completion_tokens=64,
        runtime_config={"context_window": 300, "reserved_completion_tokens": 64},
    )

    assert result.exceeded is True
    assert result.report.budget_status == "exceeded"


def test_context_budget_manager_resolves_provider_prefixed_model_window():
    manager = ContextBudgetManager()
    messages = [
        Message(role="system", content="system"),
        Message(role="user", content="latest request"),
    ]

    result = manager.fit(
        messages=messages,
        tools=[],
        model_name="openai/gpt-4o-mini",
        max_completion_tokens=64,
        runtime_config={},
    )

    assert result.report.context_limit == 128000
    assert result.exceeded is False


def test_context_budget_manager_caps_oversized_reserved_completion_tokens():
    manager = ContextBudgetManager()
    messages = [
        Message(role="system", content="system"),
        Message(role="user", content="hello"),
    ]

    result = manager.fit(
        messages=messages,
        tools=[],
        model_name="unknown-model",
        max_completion_tokens=100000,
        runtime_config={},
    )

    assert result.report.context_limit == 32768
    assert result.report.reserved_completion_tokens < 100000
    assert result.report.prompt_budget >= 3072
    assert result.exceeded is False
    assert "reserved_completion_tokens_capped_to_context_window" in result.report.notes


def test_deepseek_legacy_alias_uses_conservative_known_window():
    manager = ContextBudgetManager()
    result = manager.fit(
        messages=[Message(role="user", content="hello")],
        tools=[],
        model_name="deepseek-chat",
        max_completion_tokens=2048,
        runtime_config={},
    )
    assert result.report.context_limit == 128000


def test_rag_budget_tiers_are_token_based_and_model_capped():
    manager = ContextBudgetManager()
    messages = [Message(role="system", content="system"), Message(role="user", content="question")]
    simple = manager.plan_rag_budget(
        query="什么是TCP？", messages_without_knowledge=messages, tools=[],
        model_name="deepseek-chat", max_completion_tokens=2048, runtime_config={},
    )
    complex_plan = manager.plan_rag_budget(
        query="整理第五章TCP与UDP的主要特点", messages_without_knowledge=messages, tools=[],
        model_name="deepseek-chat", max_completion_tokens=2048, runtime_config={},
    )
    comprehensive = manager.plan_rag_budget(
        query="跨文件综合分析并逐条列出全部内容，不要遗漏", messages_without_knowledge=messages, tools=[],
        model_name="deepseek-chat", max_completion_tokens=2048, runtime_config={},
    )
    assert simple.budget_tokens == 8000
    assert complex_plan.budget_tokens == 16000
    assert comprehensive.budget_tokens == 32000

    capped = manager.plan_rag_budget(
        query="完整表格全部列出", messages_without_knowledge=messages, tools=[],
        model_name="unknown-model", max_completion_tokens=4096,
        runtime_config={"context_window": 12000},
    )
    assert capped.budget_tokens < capped.target_tokens
    assert capped.capped_by_model_window is True
