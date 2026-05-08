"""OpenAI function-calling adapter.

Converts between OpenAI's tool format and Gate's Tool format,
allowing developers to register tools from existing OpenAI manifests.

Depends on: gate-core Tool/ExecutionClass
"""
from __future__ import annotations

from typing import Any

from gatekeeper import Tool


# Map OpenAI-style hints to Gate execution classes.
# Developers can tag their OpenAI tools with a custom "x-gate-class" field,
# or the adapter falls back to a conservative default.
_DEFAULT_CLASS = "state_mutation"


def from_openai_tools(
    openai_tools: list[dict[str, Any]],
    class_map: dict[str, str] | None = None,
    default_class: str = _DEFAULT_CLASS,
) -> list[Tool]:
    """Convert OpenAI function-calling tool dicts to Gate Tools.

    Args:
        openai_tools: List of OpenAI tool dicts ({"type": "function", "function": {...}}).
        class_map: Optional mapping of tool name -> execution class.
        default_class: Fallback execution class when no mapping exists.

    Returns:
        List of Gate Tool instances.
    """
    class_map = class_map or {}
    result = []
    for entry in openai_tools:
        func = entry.get("function", entry)
        name = func["name"]
        desc = func.get("description", "")
        params = func.get("parameters", {})
        inputs = {k: v.get("type", "string") for k, v in params.get("properties", {}).items()}
        ec = class_map.get(name, func.get("x-gate-class", default_class))
        result.append(Tool(name=name, execution_class=ec, description=desc, inputs=inputs))
    return result


def to_openai_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    """Convert Gate Tools back to OpenAI function-calling format.

    Convenience wrapper — same as ToolFilter.to_openai_tools() but works
    on a plain list.
    """
    out = []
    for t in tools:
        properties = {k: {"type": v} for k, v in t.inputs.items()} if t.inputs else {}
        out.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or t.name,
                "parameters": {"type": "object", "properties": properties},
            },
        })
    return out
