"""Remote Gate server client — talks to gate-server over HTTP.

Integration contract between gate-sdk (Layer 1) and gate-server (Layer 1).
gate-server (Python/FastAPI) won the server slot competition in Cycle 2.

When wired, the SDK can operate in two modes:
  1. Local mode (default): gate-core runs in-process, no network
  2. Remote mode: delegates to a gate-server instance over HTTP

The remote client implements the same interface as GateClient so
consumers don't care which mode is active.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class RemoteGateClient(Protocol):
    """Protocol that a remote gate client must satisfy.

    Mirrors GateClient's core methods so consumers can swap
    local/remote transparently.
    """

    def add_tool(self, name: str, execution_class: str, description: str = "",
                 inputs: dict[str, str] | None = None) -> None: ...

    def filter(self, mode: float | None = None) -> Any: ...

    def export_openai(self, mode: float | None = None) -> list[dict[str, Any]]: ...

    def export_anthropic(self, mode: float | None = None) -> list[dict[str, Any]]: ...


@dataclass
class ServerEndpoints:
    """gate-server (FastAPI) endpoint map.

    Matches the routes in gate_server/routes.py.
    Uses the /api/v1 prefix that gate-server exposes.
    """
    base_url: str = "http://localhost:8900"

    @property
    def register_tools(self) -> str:
        """POST — register tools. Body: {"tools": [...]}"""
        return f"{self.base_url}/api/v1/tools/register"

    @property
    def list_tools(self) -> str:
        """GET — list registered tools."""
        return f"{self.base_url}/api/v1/tools"

    @property
    def filter(self) -> str:
        """POST — filter by mode. Body: {"mode": float}"""
        return f"{self.base_url}/api/v1/tools/filter"

    @property
    def validate(self) -> str:
        """POST — validate tool proposal. Body: {"tool_name": str, "mode": float}"""
        return f"{self.base_url}/api/v1/tools/validate"

    @property
    def export_openai(self) -> str:
        """POST — OpenAI-compatible export. Body: {"mode": float}"""
        return f"{self.base_url}/api/v1/tools/openai"

    @property
    def envelope(self) -> str:
        """POST — build authorization envelope."""
        return f"{self.base_url}/api/v1/envelope/build"

    @property
    def verify_envelope(self) -> str:
        """POST — verify envelope signature."""
        return f"{self.base_url}/api/v1/envelope/verify"

    @property
    def mode_history(self) -> str:
        """GET — mode signal history (last 100 filter ops)."""
        return f"{self.base_url}/api/v1/mode/history"

    @property
    def health(self) -> str:
        """GET — health check."""
        return f"{self.base_url}/api/v1/health"


def tools_to_server_payload(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert SDK tool dicts to gate-server registration payload."""
    return {"tools": [
        {
            "name": t["name"],
            "execution_class": t.get("execution_class", "read_only"),
            "description": t.get("description", ""),
            "inputs": t.get("inputs", {}),
        }
        for t in tools
    ]}


def filter_result_from_server(response: dict[str, Any]) -> dict[str, Any]:
    """Parse gate-server filter response into SDK-compatible shape."""
    return {
        "visible": response.get("visible", []),
        "suppressed": response.get("suppressed", []),
        "mode": response.get("mode", 0.0),
        "mode_zone": response.get("mode_zone", "normal"),
        "thresholds": response.get("thresholds", {}),
    }


def envelope_from_server(response: dict[str, Any]) -> dict[str, Any]:
    """Parse gate-server envelope response."""
    return {
        "envelope_id": response.get("envelope_id"),
        "context_id": response.get("context_id"),
        "tool_name": response.get("tool_name"),
        "allowed_tools": response.get("allowed_tools", []),
        "max_tool_calls": response.get("max_tool_calls"),
        "budget_seconds": response.get("budget_seconds"),
        "execution_mode": response.get("execution_mode"),
        "branching": response.get("branching"),
        "signature": response.get("signature"),
    }
