"""Tests for GateClient — the main SDK entry point."""
from gate_sdk import GateClient
from gate_sdk.signals import StaticSignal, EnvSignal


def test_basic_filter():
    client = GateClient(mode=0.0)
    client.add_tool("read_file", "read_only", description="Read a file")
    client.add_tool("deploy", "high_impact", description="Deploy")

    result = client.filter()
    assert "read_file" in result.visible_names
    assert "deploy" in result.visible_names


def test_crisis_suppression():
    client = GateClient(mode=0.8)
    client.add_tool("read_file", "read_only")
    client.add_tool("deploy", "high_impact")
    client.add_tool("send_email", "external_action")

    result = client.filter()
    assert result.visible_names == ["read_file"]
    assert set(result.suppressed_names) == {"deploy", "send_email"}


def test_mode_setter():
    client = GateClient(mode=0.0)
    client.add_tool("deploy", "high_impact")
    assert "deploy" in client.filter().visible_names

    client.mode = 0.9
    assert "deploy" in client.filter().suppressed_names


def test_static_signal():
    sig = StaticSignal(0.5)
    client = GateClient(mode_source=sig)
    client.add_tool("deploy", "high_impact")
    assert "deploy" in client.filter().suppressed_names

    sig.set(0.0)
    assert "deploy" in client.filter().visible_names


def test_env_signal(monkeypatch):
    monkeypatch.setenv("GATE_MODE", "0.9")
    sig = EnvSignal()
    client = GateClient(mode_source=sig)
    client.add_tool("deploy", "high_impact")
    assert "deploy" in client.filter().suppressed_names


def test_bulk_registration():
    client = GateClient()
    client.add_tools_bulk([
        {"name": "a", "execution_class": "read_only"},
        {"name": "b", "execution_class": "high_impact"},
    ])
    assert len(client.tools) == 2


def test_export_openai():
    client = GateClient(mode=0.0)
    client.add_tool("read_file", "read_only", description="Read")
    tools = client.export_openai()
    assert len(tools) == 1
    assert tools[0]["function"]["name"] == "read_file"
