"""Redis-backed mode signal — reads Gate mode from a Redis key.

Use case: multiple agents share a mode signal via Redis.
One writer (incident system, policy engine, human operator)
sets the key; all agents pick it up within poll_interval.

Requires: redis>=5.0  (add to pyproject.toml [project.optional-dependencies])

Example:
    from gate_sdk.signals.redis import RedisSignal

    signal = RedisSignal(url="redis://localhost:6379", key="gate:mode")
    client = GateClient(mode_source=signal)

    # Elsewhere, in your incident pipeline:
    # redis-cli SET gate:mode 0.8
    # All agents tighten immediately on next poll.

STUB — not wired. Needs redis-py installed and integration tested.
"""
from __future__ import annotations

import threading
import time
from typing import Optional


class RedisSignal:
    """Polls a Redis key for the current mode float.

    The key should contain a string-encoded float between 0.0 and 1.0.
    Invalid or missing values fall back to `fallback`.
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        key: str = "gate:mode",
        fallback: float = 0.0,
        poll_interval: float = 2.0,
    ) -> None:
        self._url = url
        self._key = key
        self._fallback = fallback
        self._poll_interval = poll_interval
        self._current: float = fallback
        self._client: Optional[object] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        """Begin polling Redis in a background thread."""
        try:
            import redis  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "redis package required for RedisSignal. "
                "Install with: pip install gate-sdk[redis]"
            )
        self._client = redis.from_url(self._url)
        self._stop.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the polling thread."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)

    def get_mode(self) -> float:
        """Return the most recently polled mode value."""
        return self._current

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                raw = self._client.get(self._key)  # type: ignore[union-attr]
                if raw is not None:
                    val = float(raw)
                    self._current = max(0.0, min(1.0, val))
                else:
                    self._current = self._fallback
            except (ValueError, TypeError, ConnectionError):
                self._current = self._fallback
            self._stop.wait(self._poll_interval)

    def __enter__(self) -> "RedisSignal":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
