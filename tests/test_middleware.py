"""Tests for middleware, callbacks, and context manager."""
from gate_sdk import GateClient


def test_middleware_runs():
    log = []

    def logger(mode, result):
        log.append(f"mode={mode} visible={len(result.visible)}")
        return result

    client = GateClient(mode=0.5)
    client.add_tool("a", "read_only")
    client.use(logger)
    client.filter()
    assert len(log) == 1
    assert "mode=0.5" in log[0]


def test_middleware_can_modify_result():
    """Middleware can swap the result — used for custom filtering logic."""
    from maelstrom_gate import ToolFilter

    def strip_all(mode, result):
        return ToolFilter(
            visible=(), suppressed=result.visible + result.suppressed,
            mode=result.mode, mode_status="lockdown",
            thresholds=result.thresholds,
        )

    client = GateClient(mode=0.0)
    client.add_tool("a", "read_only")
    client.use(strip_all)
    result = client.filter()
    assert len(result.visible) == 0
    assert result.mode_status == "lockdown"


def test_on_suppress_fires():
    suppressed = []

    client = GateClient(mode=0.9)
    client.add_tool("deploy", "high_impact")
    client.on_suppress(lambda tool, mode: suppressed.append(tool.name))
    client.filter()
    assert suppressed == ["deploy"]


def test_on_suppress_not_fired_when_visible():
    suppressed = []

    client = GateClient(mode=0.0)
    client.add_tool("deploy", "high_impact")
    client.on_suppress(lambda tool, mode: suppressed.append(tool.name))
    client.filter()
    assert suppressed == []


def test_on_mode_change_fires():
    changes = []

    client = GateClient(mode=0.0)
    client.add_tool("a", "read_only")
    client.on_mode_change(lambda old, new: changes.append((old, new)))

    client.filter(mode=0.0)  # first call, no previous mode
    client.filter(mode=0.5)  # mode changed
    client.filter(mode=0.5)  # same mode, no fire
    client.filter(mode=0.9)  # changed again

    assert changes == [(0.0, 0.5), (0.5, 0.9)]


def test_override_mode_context_manager():
    client = GateClient(mode=0.0)
    client.add_tool("deploy", "high_impact")

    assert "deploy" in client.filter().visible_names

    with client.override_mode(0.9):
        assert "deploy" in client.filter().suppressed_names

    # Back to normal after context manager
    assert "deploy" in client.filter().visible_names


def test_override_mode_restores_dynamic_source():
    from gate_sdk.signals import StaticSignal

    sig = StaticSignal(0.2)
    client = GateClient(mode_source=sig)
    client.add_tool("deploy", "high_impact")

    with client.override_mode(0.9):
        assert client.mode == 0.9

    assert client.mode == 0.2  # original source restored
