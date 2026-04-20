#!/usr/bin/env python3
"""SDK + Compliance wired demo — gate-sdk feeding gate-compliance in real time.

This is the first LIVE WIRING between Layer 1 (gate-sdk) and Layer 2
(gate-compliance). Every filter() call through the SDK automatically
records to the compliance audit trail. No manual recording needed.

Run: python examples/compliance_wired.py
Requires: pip install -e ../gate-sdk -e ../gate-compliance
"""
from __future__ import annotations

import os
import tempfile

from gate_sdk import GateClient
from gate_sdk.adapters.openai import from_openai_tools
from gate_compliance import AuditStore, ComplianceCollector, ComplianceReporter
from gate_compliance.alerts import run_all_checks

# -- Setup: SDK client with compliance hooks wired in --

db_path = os.path.join(tempfile.gettempdir(), "sdk_compliance_wired.db")
if os.path.exists(db_path):
    os.remove(db_path)

store = AuditStore(db_path)
collector = ComplianceCollector(store, context_id="wired-demo")

client = GateClient(mode=0.0)

# Wire compliance hooks into the SDK
client.use(collector.filter_hook)
client.on_suppress(collector.suppress_hook)

# Register tools from OpenAI format
openai_tools = [
    {"type": "function", "function": {"name": "read_file", "description": "Read a file",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write a file",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "deploy", "description": "Deploy to prod",
     "parameters": {"type": "object", "properties": {"env": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "send_alert", "description": "Send PagerDuty",
     "parameters": {"type": "object", "properties": {"msg": {"type": "string"}}}}},
]

class_map = {
    "read_file": "read_only",
    "write_file": "state_mutation",
    "deploy": "high_impact",
    "send_alert": "external_action",
}

gate_tools = from_openai_tools(openai_tools, class_map=class_map)
for t in gate_tools:
    client.add_tool(t.name, t.execution_class, t.description, t.inputs)

# -- Run: escalate threat, SDK records everything automatically --

print("=" * 60)
print("  SDK + COMPLIANCE WIRED DEMO")
print("  Every SDK filter() call auto-records to audit trail")
print("=" * 60)

for mode in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 0.3, 0.0]:
    result = client.filter(mode)
    status = result.mode_zone.upper()
    print(f"\n  mode={mode:.1f} [{status:8s}] visible={len(result.visible)} suppressed={len(result.suppressed)}")
    if result.suppressed:
        print(f"    blocked: {', '.join(result.suppressed_names)}")

# Record an envelope event manually (SDK doesn't auto-capture these yet)
collector.record_envelope_issued("read_file", 0.0, envelope_id="env-auto-1")
collector.record_envelope_verified("read_file", 0.0, envelope_id="env-auto-1", valid=True)

# -- Report: compliance report generated from live SDK data --

print(f"\n{'=' * 60}")
reporter = ComplianceReporter(store)
print(reporter.text_report())

# -- Alerts --

alerts = run_all_checks(store)
if alerts:
    print("\n  ALERTS:")
    for a in alerts:
        print(f"    [{a.severity.upper()}] {a.alert_type}: {a.message}")
else:
    print("\n  No compliance alerts.")

print(f"\n  Audit database: {db_path}")
print(f"  Events recorded: {store.count()}")
print(f"{'=' * 60}")
print("  SDK + Compliance: wired and working.")
print(f"{'=' * 60}")
