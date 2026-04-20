"""LangChain adapter — convert between Gate tools and LangChain tool format.

LangChain tools use a different shape than OpenAI/Anthropic:
    - Each tool is a dict with 'name', 'description', 'args_schema' (Pydantic model or JSON schema)
    - Or a BaseTool subclass with those as attributes

This adapter handles the dict/JSON-schema form. For BaseTool subclasses,
users should extract the schema dict first.

STUB — needs validation against LangChain 0.2+ tool format.
Requires: langchain-core>=0.2 (optional dependency)

Example:
    from gate_sdk.adapters.langchain import from_langchain_tools, to_langchain_tools

    gate_tools = from_langchain_tools(lc_tools, class_map={"search": "read_only"})
    client = GateClient(mode=0.0)
    for t in gate_tools:
        client.add_tool(t.name, t.execution_class, t.description, t.inputs)

    # Export back to LangChain after filtering
    filtered = client.filter(mode=0.3)
    lc_out = to_langchain_tools(filtered.visible)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GateTool:
    """Intermediate representation for adapter output."""
    name: str
    execution_class: str
    description: str
    inputs: dict[str, Any]


def from_langchain_tools(
    lc_tools: list[dict[str, Any]],
    class_map: dict[str, str] | None = None,
    default_class: str = "state_mutation",
) -> list[GateTool]:
    """Convert LangChain tool dicts to Gate tools.

    Args:
        lc_tools: List of LangChain tool definitions.
            Each should have 'name', 'description', and optionally
            'args_schema' (JSON schema dict).
        class_map: Maps tool name -> execution class.
        default_class: Fallback class for unmapped tools.
            Defaults to state_mutation (conservative).

    Returns:
        List of GateTool instances ready for client.add_tool().
    """
    class_map = class_map or {}
    result = []
    for tool in lc_tools:
        name = tool["name"]
        desc = tool.get("description", "")
        schema = tool.get("args_schema", {})

        # LangChain sometimes wraps schema in a Pydantic model class.
        # If it's not a dict, try to pull .schema() from it.
        if not isinstance(schema, dict):
            if hasattr(schema, "schema"):
                schema = schema.schema()
            elif hasattr(schema, "model_json_schema"):
                schema = schema.model_json_schema()
            else:
                schema = {}

        result.append(GateTool(
            name=name,
            execution_class=class_map.get(name, default_class),
            description=desc,
            inputs=schema,
        ))
    return result


def to_langchain_tools(tools: list[Any]) -> list[dict[str, Any]]:
    """Convert Gate tools back to LangChain tool dict format.

    Args:
        tools: List of Tool objects (from gate-core) with
            name, description, and inputs attributes.

    Returns:
        List of dicts in LangChain tool format.
    """
    result = []
    for t in tools:
        result.append({
            "name": t.name,
            "description": t.description,
            "args_schema": getattr(t, "inputs", {}),
        })
    return result
