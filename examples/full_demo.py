#!/usr/bin/env python3
"""Maelstrom Gate SDK -- Full Demo

An AI coding assistant has 8 tools. Watch what happens as the
threat level rises from calm to crisis.

Run: python examples/full_demo.py
"""
from gate_sdk import GateClient
from gate_sdk.adapters.openai import from_openai_tools
from gate_sdk.adapters.anthropic import to_anthropic_tools
from gate_sdk.signals import EnvSignal

# -- Step 1: Register tools from OpenAI format ------------------------
# Imagine these came from your existing OpenAI function-calling setup.

openai_manifest = [
    {"type": "function", "function": {
        "name": "read_file", "description": "Read a source file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "search_code", "description": "Search codebase with regex",
        "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "explain_code", "description": "Explain what code does",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "write_file", "description": "Write content to a file",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "run_tests", "description": "Execute test suite",
        "parameters": {"type": "object", "properties": {"suite": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "send_slack", "description": "Send a Slack message",
        "parameters": {"type": "object", "properties": {"channel": {"type": "string"}, "msg": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "deploy", "description": "Deploy to production",
        "parameters": {"type": "object", "properties": {"version": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "drop_table", "description": "Drop a database table",
        "parameters": {"type": "object", "properties": {"table": {"type": "string"}}},
    }},
]

# Map each tool to its Gate execution class
CLASS_MAP = {
    "read_file":    "read_only",
    "search_code":  "read_only",
    "explain_code": "advisory",
    "write_file":   "state_mutation",
    "run_tests":    "state_mutation",
    "send_slack":   "external_action",
    "deploy":       "high_impact",
    "drop_table":   "high_impact",
}

# Convert from OpenAI format to Gate tools
gate_tools = from_openai_tools(openai_manifest, class_map=CLASS_MAP)

# -- Step 2: Create a GateClient --------------------------------------

client = GateClient(mode=0.0)
for t in gate_tools:
    client.add_tool(t.name, t.execution_class, t.description, t.inputs)

# -- Step 3: Add audit middleware -------------------------------------

audit_log = []

def audit_middleware(mode, result):
    """Log every filter decision for compliance."""
    audit_log.append({
        "mode": mode,
        "zone": result.mode_zone,
        "visible": result.visible_names,
        "suppressed": result.suppressed_names,
    })
    return result

client.use(audit_middleware)

# Track suppressions
suppression_events = []
client.on_suppress(lambda tool, mode: suppression_events.append(
    f"  BLOCKED: {tool.name} ({tool.execution_class}) at mode {mode}"
))

# Track mode transitions
client.on_mode_change(lambda old, new: print(
    f"\n  >> Mode shift: {old:.1f} -> {new:.1f}"
))

# -- Step 4: Simulate escalating threat -------------------------------

print("=" * 60)
print("  MAELSTROM GATE SDK -- LIVE DEMO")
print("  AI Coding Assistant under escalating threat")
print("=" * 60)

scenarios = [
    (0.0,  "Routine coding session -- all tools available"),
    (0.2,  "Normal operations -- developer is working"),
    (0.4,  "Anomaly detected -- high-impact tools locked"),
    (0.5,  "Elevated alert -- only safe actions allowed"),
    (0.7,  "Crisis -- agent locked to read-only + advisory"),
    (1.0,  "Maximum threat -- tightest possible restrictions"),
]

for mode, description in scenarios:
    suppression_events.clear()
    result = client.filter(mode)

    print(f"\n{'-' * 60}")
    print(f"  MODE {mode:.1f} | {result.mode_zone.upper()} | {description}")
    print(f"{'-' * 60}")
    print(f"  Available ({len(result.visible)}):")
    for t in result.visible:
        print(f"    [{t.execution_class:17s}] {t.name}")
    if result.suppressed:
        print(f"  Suppressed ({len(result.suppressed)}):")
        for line in suppression_events:
            print(line)

# -- Step 5: Authorization envelope demo ------------------------------

print(f"\n{'=' * 60}")
print("  AUTHORIZATION ENVELOPES")
print(f"{'=' * 60}")

SIGNING_KEY = "demo-secret-key-do-not-use-in-prod"

# Authorize a safe tool
env = client.authorize("read_file", signing_key=SIGNING_KEY, context_id="demo-session")
print(f"\n  Envelope for 'read_file' at mode 0.0:")
print(f"    ID:         {env.envelope_id}")
print(f"    Budget:     {env.budget_seconds}s")
print(f"    Max calls:  {env.max_tool_calls}")
print(f"    Exec mode:  {env.execution_mode}")
print(f"    Branching:  {env.branching}")
print(f"    Signature:  {env.signature[:32]}...")
print(f"    Valid:      {client.verify(env, SIGNING_KEY)}")

# Show how crisis tightens the envelope
with client.override_mode(0.8):
    env_crisis = client.authorize("read_file", signing_key=SIGNING_KEY, context_id="crisis-session")
    print(f"\n  Same tool at mode 0.8 (crisis):")
    print(f"    Budget:     {env_crisis.budget_seconds}s (was {env.budget_seconds}s)")
    print(f"    Max calls:  {env_crisis.max_tool_calls} (was {env.max_tool_calls})")
    print(f"    Exec mode:  {env_crisis.execution_mode} (was {env.execution_mode})")

# Try to authorize a suppressed tool
print(f"\n  Attempting to authorize 'deploy' at mode 0.8:")
try:
    with client.override_mode(0.8):
        client.authorize("deploy", signing_key=SIGNING_KEY)
except ValueError as e:
    print(f"    DENIED: {e}")

# -- Step 6: Export for Anthropic -------------------------------------

print(f"\n{'=' * 60}")
print("  FRAMEWORK EXPORT")
print(f"{'=' * 60}")

anthropic_tools = client.export_anthropic(mode=0.5)
print(f"\n  Anthropic tools at mode 0.5 (elevated):")
for t in anthropic_tools:
    print(f"    {t['name']}: {t['description']}")

openai_tools = client.export_openai(mode=0.5)
print(f"\n  OpenAI tools at mode 0.5 (elevated):")
for t in openai_tools:
    print(f"    {t['function']['name']}: {t['function']['description']}")

# -- Step 7: Audit log ------------------------------------------------

print(f"\n{'=' * 60}")
print(f"  AUDIT LOG ({len(audit_log)} filter events captured)")
print(f"{'=' * 60}")
for i, entry in enumerate(audit_log):
    print(f"  [{i+1}] mode={entry['mode']:.1f} zone={entry['zone']:8s} "
          f"visible={len(entry['visible'])} suppressed={len(entry['suppressed'])}")

print(f"\n{'=' * 60}")
print("  Demo complete. Gate SDK protects your agent at every level.")
print(f"{'=' * 60}")
