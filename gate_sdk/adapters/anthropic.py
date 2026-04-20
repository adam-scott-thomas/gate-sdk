"""Anthropic tool-use adapter.

Converts between Anthropic's tool format and Gate's Tool format.
Anthropic tools use {"name", "description", "input_schema"} shape.

Depends on: gate-core Tool/ExecutionClass
"""
from __future__ import annotations

from typing import Any

from maelstrom_gate import Tool

_DEFAULT_CLASS = "state_mutation"


def from_anthropic_tools(
    anthropic_tools: list[dict[str, Any]],
    class_map: dict[str, str] | None = None,
    default_class: str = _DEFAULT_CLASS,
) -> list[Tool]:
    """Convert Anthropic tool dicts to Gate Tools.

    Args:
        anthropic_tools: List of Anthropic tool dicts
            ({"name": "...", "description": "...", "input_schema": {...}}).
        class_map: Optional mapping of tool name -> execution class.
        default_class: Fallback execution class when no mapping exists.
    """
    class_map = class_map or {}
    result = []
    for entry in anthropic_tools:
        name = entry["name"]
        desc = entry.get("description", "")
        schema = entry.get("input_schema", {})
        inputs = {k: v.get("type", "string") for k, v in schema.get("properties", {}).items()}
        ec = class_map.get(name, entry.get("x-gate-class", default_class))
        result.append(Tool(name=name, execution_class=ec, description=desc, inputs=inputs))
    return result


def to_anthropic_tools(tools: list[Tool]) -> list[dict[str, Any]]:
    """Convert Gate Tools to Anthropic tool format."""
    out = []
    for t in tools:
        properties = {k: {"type": v} for k, v in t.inputs.items()} if t.inputs else {}
        out.append({
            "name": t.name,
            "description": t.description or t.name,
            "input_schema": {
                "type": "object",
                "properties": properties,
            },
        })
    return out
