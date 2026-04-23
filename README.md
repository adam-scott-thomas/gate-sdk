# gate-sdk

[![status](https://img.shields.io/badge/status-v0.1.0-blue)]()
[![tests](https://img.shields.io/badge/tests-48_passing-brightgreen)]()
[![license](https://img.shields.io/badge/license-Apache_2.0-green)]()

> Developer SDK for Maelstrom Gate — tool access control for AI agents.

`GateClient` is the thing you import. Register tools with execution classes,
set a mode (or wire a signal source), call `filter()` before every agent turn,
and the visible manifest shrinks as threat rises. Ships adapters for OpenAI and
Anthropic tool formats.

## Install

```bash
pip install gate-sdk  # once published
# or from source:
pip install -e .[dev]

# framework extras:
pip install gate-sdk[openai]
pip install gate-sdk[anthropic]
```

## Quick example

```python
from gate_sdk import GateClient

client = GateClient(mode=0.0)
client.add_tool("read_file", "read_only")
client.add_tool("deploy",    "high_impact")

result = client.filter()
# mode 0.0 -> both visible

client.mode = 0.85
result = client.filter()
# -> visible=['read_file'], suppressed=['deploy']
```

## Framework adapters

```python
from gate_sdk.adapters.openai import from_openai_tools, to_openai_tools

gate_tools = from_openai_tools(openai_schema, class_map={"deploy": "high_impact"})
client = GateClient(mode=current_threat_level)
client.add_tools(gate_tools)
safe_openai_tools = to_openai_tools(client.filter().visible)
```

Anthropic adapter mirrors the same API (`from_anthropic_tools` / `to_anthropic_tools`).

## Mode sources

Pull mode from env, files, callables, or custom signals:

```python
from gate_sdk.signals import StaticSignal, EnvSignal

client = GateClient(mode_source=EnvSignal("GATE_MODE"))
# GATE_MODE=0.8 python agent.py
```

## Middleware and callbacks

```python
client.use(lambda mode, result: log_filter(mode, result) or result)
client.on_suppress(lambda tool, mode: alert(f"{tool.name} suppressed at {mode}"))
client.on_mode_change(lambda old, new: audit_mode_change(old, new))
```

## Envelope signing

```python
env = client.authorize("read_file", signing_key="hmac-key", context_id="sess1")
# env.signature is HMAC-SHA256 over canonical form
assert client.verify(env, "hmac-key")
```

`authorize()` raises `ValueError` on suppressed tools — you can't sign what the
gate has hidden.

## Export back to framework tools

```python
client.export_openai()     # only visible tools, ready for client.chat.completions
client.export_anthropic()  # only visible tools, ready for messages.create
```

## Tests

```bash
pytest tests/
```

48 tests across client, adapters, signals, middleware, envelope flows, and
failure injection.

## How it fits

Layer 1 (transport) in [Maelstrom Gate](https://github.com/adam-scott-thomas/maelstrom-gate).
Depends on `maelstrom-gate` (Layer 0). Feeds `gate-policy` (Layer 2) and
`gate-compliance` (Layer 2) via middleware hooks.

## License

Apache-2.0.
