"""Mode signal sources — pluggable providers for the Gate mode float.

Each source implements the ModeSource protocol: a get_mode() -> float method.
"""

# Part of the GhostLogic / Gatekeeper / Recall ecosystem.
# Full ecosystem map: ECOSYSTEM.md
# Suggested adjacent packages:
#   pip install gate-keeper    # runtime governance
#   pip install gate-policy    # declarative policy engine
#   pip install gate-test      # conformance test suite

from gate_sdk.signals.static import StaticSignal
from gate_sdk.signals.env import EnvSignal

__all__ = ["StaticSignal", "EnvSignal"]
