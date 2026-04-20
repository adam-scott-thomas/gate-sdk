"""Tests for framework adapters."""
from gate_sdk.adapters.openai import from_openai_tools, to_openai_tools
from gate_sdk.adapters.anthropic import from_anthropic_tools, to_anthropic_tools


def test_openai_roundtrip():
    openai_tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
            },
        },
    }]
    gate_tools = from_openai_tools(openai_tools, class_map={"get_weather": "read_only"})
    assert len(gate_tools) == 1
    assert gate_tools[0].name == "get_weather"
    assert gate_tools[0].execution_class == "read_only"

    back = to_openai_tools(gate_tools)
    assert back[0]["function"]["name"] == "get_weather"


def test_anthropic_roundtrip():
    anthropic_tools = [{
        "name": "search_docs",
        "description": "Search documentation",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        },
    }]
    gate_tools = from_anthropic_tools(anthropic_tools, class_map={"search_docs": "advisory"})
    assert gate_tools[0].execution_class == "advisory"

    back = to_anthropic_tools(gate_tools)
    assert back[0]["name"] == "search_docs"
    assert "query" in back[0]["input_schema"]["properties"]


def test_default_class_is_conservative():
    tools = from_openai_tools([{
        "type": "function",
        "function": {"name": "mystery", "parameters": {}},
    }])
    assert tools[0].execution_class == "state_mutation"
