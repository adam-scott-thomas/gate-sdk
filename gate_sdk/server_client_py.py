"""Legacy stub — merged into gate_sdk.server_client.

This file was a Creator 2 stub for gate-server (Python) endpoints.
The consolidated implementation now lives in server_client.py, which
targets gate-server (the competition winner) with correct /api/v1 routes.

Kept as a re-export for backwards compatibility.
"""
from gate_sdk.server_client import (
    ServerEndpoints,
    RemoteGateClient,
    tools_to_server_payload,
    filter_result_from_server,
    envelope_from_server,
)

# Alias for code that imported from this module
PythonServerEndpoints = ServerEndpoints

__all__ = [
    "PythonServerEndpoints",
    "ServerEndpoints",
    "RemoteGateClient",
    "tools_to_server_payload",
    "filter_result_from_server",
    "envelope_from_server",
]
