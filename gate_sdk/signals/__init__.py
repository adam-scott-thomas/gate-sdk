"""Mode signal sources — pluggable providers for the Gate mode float.

Each source implements the ModeSource protocol: a get_mode() -> float method.
"""
from gate_sdk.signals.static import StaticSignal
from gate_sdk.signals.env import EnvSignal

__all__ = ["StaticSignal", "EnvSignal"]
