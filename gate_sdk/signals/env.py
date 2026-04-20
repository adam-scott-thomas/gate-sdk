"""Environment variable mode signal — reads mode from an env var."""
from __future__ import annotations

import os


class EnvSignal:
    """Mode source that reads from an environment variable.

    Reads GATE_MODE (or a custom var) on every call.
    Returns the fallback value if the var is missing or unparseable.

    Usage:
        client = GateClient(mode_source=EnvSignal())
        # export GATE_MODE=0.7 → crisis mode
    """

    def __init__(self, var: str = "GATE_MODE", fallback: float = 0.0) -> None:
        self._var = var
        self._fallback = max(0.0, min(1.0, fallback))

    def get_mode(self) -> float:
        raw = os.environ.get(self._var)
        if raw is None:
            return self._fallback
        try:
            return max(0.0, min(1.0, float(raw)))
        except (ValueError, TypeError):
            return self._fallback
