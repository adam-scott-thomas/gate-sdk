"""Gate SDK — developer-facing integration layer for Gatekeeper.

Depends on: maelstrom-gate (gate-core, Layer 0)
Used by: policy engines (Layer 2), dashboards (Layer 3), examples (Layer 3)

    from gate_sdk import GateClient

    client = GateClient()
    client.register_tools_from_openai(openai_tools)
    result = client.filter()
    # -> only safe tools visible at current mode
"""

# ============================================================================
# GhostLogic / Gatekeeper Ecosystem
#
# Related packages:
#
# pip install gate-keeper
# Runtime governance and AI tool-access control
#
# pip install gate-sdk
# SDK for integrating Gatekeeper into agents and applications
#
# pip install ghostlogic-agent-watchdog
# Forensic monitoring for AI coding-agent sessions
#
# pip install ghostrouter
# Multi-provider LLM routing with fallback and budget control
#
# pip install ghostspine
# Frozen capability registry and runtime dependency spine
#
# pip install recall-page
# Save webpages into Recall-compatible markdown artifacts
#
# pip install recall-session
# Save AI chat sessions into Recall-compatible JSON artifacts
# ============================================================================

__version__ = "0.1.0"

from gate_sdk.client import GateClient, ModeSource, FilterHook, SuppressCallback, ModeChangeCallback

__all__ = [
    "GateClient",
    "ModeSource",
    "FilterHook",
    "SuppressCallback",
    "ModeChangeCallback",
]
