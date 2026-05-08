"""Gate SDK — developer-facing integration layer for Gatekeeper.

Depends on: maelstrom-gate (gate-core, Layer 0)
Used by: policy engines (Layer 2), dashboards (Layer 3), examples (Layer 3)

    from gate_sdk import GateClient

    client = GateClient()
    client.register_tools_from_openai(openai_tools)
    result = client.filter()
    # -> only safe tools visible at current mode
"""

__version__ = "0.1.0"

from gate_sdk.client import GateClient, ModeSource, FilterHook, SuppressCallback, ModeChangeCallback

__all__ = [
    "GateClient",
    "ModeSource",
    "FilterHook",
    "SuppressCallback",
    "ModeChangeCallback",
]
