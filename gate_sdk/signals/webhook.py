"""Webhook mode signal — receives mode updates via HTTP POST.

Requires: starlette, uvicorn (optional dependency group "webhook")
"""
from __future__ import annotations

import threading


class WebhookSignal:
    """Mode source updated by incoming HTTP requests.

    Exposes a tiny HTTP endpoint that accepts POST {"mode": 0.7}.
    Thread-safe — the mode is read by the Gate client on the main thread
    and written by the webhook handler thread.

    Usage:
        signal = WebhookSignal()
        signal.start(port=8900)  # background thread
        client = GateClient(mode_source=signal)

        # POST http://localhost:8900/ {"mode": 0.7}
        # -> client.filter() now returns crisis-level filtering
    """

    def __init__(self, initial: float = 0.0) -> None:
        self._mode = max(0.0, min(1.0, initial))
        self._lock = threading.Lock()
        self._server_thread: threading.Thread | None = None

    def get_mode(self) -> float:
        with self._lock:
            return self._mode

    def set_mode(self, value: float) -> None:
        with self._lock:
            self._mode = max(0.0, min(1.0, value))

    def start(self, host: str = "127.0.0.1", port: int = 8900) -> None:
        """Start the webhook receiver in a background thread."""
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        import uvicorn

        signal = self

        async def receive_mode(request: Request) -> JSONResponse:
            body = await request.json()
            mode = float(body.get("mode", 0.0))
            signal.set_mode(mode)
            return JSONResponse({"mode": signal.get_mode(), "status": "ok"})

        async def get_status(request: Request) -> JSONResponse:
            return JSONResponse({"mode": signal.get_mode()})

        app = Starlette(routes=[
            Route("/", receive_mode, methods=["POST"]),
            Route("/", get_status, methods=["GET"]),
        ])

        def _run() -> None:
            uvicorn.run(app, host=host, port=port, log_level="warning")

        self._server_thread = threading.Thread(target=_run, daemon=True)
        self._server_thread.start()
