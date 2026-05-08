"""Failure injection tests for gate-sdk — what happens when things go wrong.

Tests for:
- Bad mode values (negative, >1, NaN-adjacent)
- Empty tool registrations
- Duplicate tool names
- Middleware that throws exceptions
- Suppress callbacks that throw
- Mode change callbacks that throw
- Override mode edge cases
- Export with no tools
- Authorize edge cases
"""
from gate_sdk import GateClient
from gatekeeper import ToolFilter
import pytest


# --- Bad mode values ---


def test_filter_negative_mode():
    """Negative mode should still work (gate-core clamps behavior)."""
    client = GateClient(mode=0.0)
    client.add_tool("deploy", "high_impact")
    result = client.filter(mode=-1.0)
    # Negative mode = below all thresholds = nothing suppressed
    assert "deploy" in result.visible_names


def test_filter_mode_above_one():
    """Mode > 1.0 should suppress everything except read_only/advisory."""
    client = GateClient(mode=0.0)
    client.add_tool("read", "read_only")
    client.add_tool("deploy", "high_impact")
    client.add_tool("write", "state_mutation")
    result = client.filter(mode=5.0)
    assert "read" in result.visible_names
    assert "deploy" in result.suppressed_names
    assert "write" in result.suppressed_names


def test_mode_setter_clamps():
    """Mode setter should clamp to [0.0, 1.0]."""
    client = GateClient(mode=0.5)
    client.mode = -1.0
    assert client.mode == 0.0
    client.mode = 2.0
    assert client.mode == 1.0


def test_mode_setter_with_dynamic_source_raises():
    """Setting mode directly with a dynamic source should raise."""
    from gate_sdk.signals import StaticSignal
    client = GateClient(mode_source=StaticSignal(0.5))
    with pytest.raises(AttributeError, match="dynamic ModeSource"):
        client.mode = 0.8


# --- Empty/edge tool registration ---


def test_filter_no_tools():
    """Filtering with zero tools should return empty results."""
    client = GateClient(mode=0.5)
    result = client.filter()
    assert result.visible_names == []
    assert result.suppressed_names == []


def test_add_tool_empty_name():
    """Empty tool name should still register (gate-core doesn't validate names)."""
    client = GateClient(mode=0.0)
    client.add_tool("", "read_only")
    assert len(client.tools) == 1
    assert client.tools[0].name == ""


def test_add_duplicate_tool_name():
    """Duplicate tool name should overwrite the previous registration."""
    client = GateClient(mode=0.0)
    client.add_tool("deploy", "high_impact", description="v1")
    client.add_tool("deploy", "read_only", description="v2")
    result = client.filter(mode=0.5)
    # If overwritten to read_only, should be visible at 0.5
    assert "deploy" in result.visible_names


def test_remove_nonexistent_tool():
    """Removing a tool that doesn't exist should not crash."""
    client = GateClient(mode=0.0)
    client.add_tool("read", "read_only")
    client.remove_tool("nonexistent")  # should not raise
    assert len(client.tools) == 1


def test_bulk_register_empty_list():
    """Bulk register with empty list should be a no-op."""
    client = GateClient(mode=0.0)
    client.add_tools_bulk([])
    assert len(client.tools) == 0


def test_unknown_execution_class():
    """Unknown execution class should be treated as high_impact (per spec)."""
    client = GateClient(mode=0.0)
    client.add_tool("mystery", "totally_made_up")
    result = client.filter(mode=0.4)
    # high_impact threshold is 0.35, so at 0.4 it should be suppressed
    assert "mystery" in result.suppressed_names


# --- Middleware failure modes ---


def test_middleware_exception_propagates():
    """Middleware that throws should propagate the exception."""
    def exploding_hook(mode, result):
        raise RuntimeError("middleware boom")

    client = GateClient(mode=0.0)
    client.add_tool("read", "read_only")
    client.use(exploding_hook)

    with pytest.raises(RuntimeError, match="middleware boom"):
        client.filter()


def test_middleware_returns_none():
    """Middleware returning None should cause an AttributeError on next hook."""
    def bad_hook(mode, result):
        return None  # forgot to return result

    client = GateClient(mode=0.0)
    client.add_tool("read", "read_only")
    client.use(bad_hook)
    # With one middleware returning None, filter() returns None
    result = client.filter()
    assert result is None


def test_multiple_middleware_chain_order():
    """Middleware should run in registration order."""
    order = []

    def hook_a(mode, result):
        order.append("a")
        return result

    def hook_b(mode, result):
        order.append("b")
        return result

    client = GateClient(mode=0.0)
    client.add_tool("read", "read_only")
    client.use(hook_a)
    client.use(hook_b)
    client.filter()
    assert order == ["a", "b"]


# --- Callback failure modes ---


def test_suppress_callback_exception_propagates():
    """Suppress callback that throws should propagate."""
    def bad_cb(tool, mode):
        raise ValueError("suppress boom")

    client = GateClient(mode=0.9)
    client.add_tool("deploy", "high_impact")
    client.on_suppress(bad_cb)

    with pytest.raises(ValueError, match="suppress boom"):
        client.filter()


def test_mode_change_callback_exception_propagates():
    """Mode change callback that throws should propagate."""
    def bad_cb(old, new):
        raise TypeError("mode change boom")

    client = GateClient(mode=0.0)
    client.add_tool("read", "read_only")
    client.on_mode_change(bad_cb)

    client.filter(mode=0.0)  # first call, no previous
    with pytest.raises(TypeError, match="mode change boom"):
        client.filter(mode=0.5)  # mode changed, callback fires


# --- Override mode edge cases ---


def test_override_mode_nested():
    """Nested override_mode contexts should work correctly."""
    client = GateClient(mode=0.0)
    client.add_tool("deploy", "high_impact")

    assert "deploy" in client.filter().visible_names  # mode 0.0

    with client.override_mode(0.5):
        assert "deploy" in client.filter().suppressed_names  # mode 0.5

        with client.override_mode(0.0):
            assert "deploy" in client.filter().visible_names  # mode 0.0

        assert "deploy" in client.filter().suppressed_names  # back to 0.5

    assert "deploy" in client.filter().visible_names  # back to 0.0


def test_override_mode_exception_restores():
    """Override mode should restore even if an exception occurs."""
    client = GateClient(mode=0.0)
    client.add_tool("deploy", "high_impact")

    try:
        with client.override_mode(0.9):
            raise RuntimeError("oops")
    except RuntimeError:
        pass

    assert client.mode == 0.0  # restored


# --- Export edge cases ---


def test_export_openai_no_tools():
    """OpenAI export with no tools should return empty list."""
    client = GateClient(mode=0.0)
    assert client.export_openai() == []


def test_export_anthropic_no_tools():
    """Anthropic export with no tools should return empty list."""
    client = GateClient(mode=0.0)
    assert client.export_anthropic() == []


# --- Authorize edge cases ---


def test_authorize_nonexistent_tool():
    """Authorizing a tool that doesn't exist should raise."""
    client = GateClient(mode=0.0)
    client.add_tool("read", "read_only")
    with pytest.raises(ValueError, match="suppressed"):
        client.authorize("nonexistent", signing_key="key")


def test_verify_with_wrong_key():
    """Verifying with wrong key should return False."""
    client = GateClient(mode=0.0)
    client.add_tool("read", "read_only")
    env = client.authorize("read", signing_key="correct-key")
    assert not client.verify(env, "wrong-key")
