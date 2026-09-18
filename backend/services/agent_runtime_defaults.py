from __future__ import annotations


DEFAULT_AGENT_TOOL_IDS: list[str] = [
    "websearch",
    "calculate",
]


def default_agent_tool_ids() -> list[str]:
    return list(DEFAULT_AGENT_TOOL_IDS)
