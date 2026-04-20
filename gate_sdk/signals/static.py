"""Static mode signal — returns a fixed value, adjustable at runtime."""
from __future__ import annotations


class StaticSignal:
    """Mode source that returns a fixed float.

    Useful for testing, demos, and manual mode control.
    """

    def __init__(self, value: float = 0.0) -> None:
        self._value = max(0.0, min(1.0, value))

    def get_mode(self) -> float:
        return self._value

    def set(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))
