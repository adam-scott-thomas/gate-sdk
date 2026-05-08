"""GateClient — the main SDK entry point.

Wraps gate-core's Gate with:
- Pluggable mode signal sources
- Framework-agnostic tool registration
- Filter-and-export in one call
- Middleware hooks (intercept every filter call)
- Event callbacks (on_suppress, on_mode_change)
- Context manager for temporary mode overrides
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Protocol, Callable

from gatekeeper import Gate, Tool, ToolFilter, AuthorizationEnvelope, build_envelope, verify_envelope


FilterHook = Callable[[float, ToolFilter], ToolFilter]
SuppressCallback = Callable[[Tool, float], None]
ModeChangeCallback = Callable[[float, float], None]


class ModeSource(Protocol):
    """Protocol for mode signal providers.

    Implementations return the current mode float in [0.0, 1.0].
    """
    def get_mode(self) -> float: ...


class _StaticMode:
    """Default mode source — returns a fixed value."""
    def __init__(self, value: float = 0.0) -> None:
        self._value = max(0.0, min(1.0, value))

    def get_mode(self) -> float:
        return self._value

    def set(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))


class GateClient:
    """High-level SDK client for Gatekeeper.

    Usage:
        client = GateClient(mode=0.0)
        client.add_tool("read_file", "read_only", description="Read a file")
        client.add_tool("deploy", "high_impact", description="Deploy to prod")

        result = client.filter()
        print(result.visible_names)  # ['read_file'] at high mode

        # Or use a dynamic mode source
        client = GateClient(mode_source=my_redis_source)
    """

    def __init__(
        self,
        mode: float = 0.0,
        mode_source: ModeSource | None = None,
        thresholds: dict[str, float | None] | None = None,
    ) -> None:
        self._gate = Gate(thresholds=thresholds)
        if mode_source is not None:
            self._mode_source = mode_source
        else:
            self._mode_source = _StaticMode(mode)
        self._middleware: list[FilterHook] = []
        self._on_suppress: list[SuppressCallback] = []
        self._on_mode_change: list[ModeChangeCallback] = []
        self._last_mode: float | None = None

    @property
    def mode(self) -> float:
        return self._mode_source.get_mode()

    @mode.setter
    def mode(self, value: float) -> None:
        if isinstance(self._mode_source, _StaticMode):
            self._mode_source.set(value)
        else:
            raise AttributeError(
                "Cannot set mode directly when using a dynamic ModeSource. "
                "Update the source instead."
            )

    def add_tool(
        self,
        name: str,
        execution_class: str = "read_only",
        description: str = "",
        inputs: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Register a single tool."""
        self._gate.add_tool(Tool(
            name=name,
            execution_class=execution_class,
            description=description,
            inputs=inputs or {},
            metadata=metadata or {},
        ))

    def add_tools_bulk(self, tools: list[dict[str, Any]]) -> None:
        """Register tools from a list of dicts.

        Each dict needs at minimum: {"name": "...", "execution_class": "..."}
        """
        for spec in tools:
            self.add_tool(
                name=spec["name"],
                execution_class=spec.get("execution_class", "read_only"),
                description=spec.get("description", ""),
                inputs=spec.get("inputs"),
                metadata=spec.get("metadata"),
            )

    def use(self, hook: FilterHook) -> None:
        """Add middleware that runs on every filter() call.

        The hook receives (mode, result) and returns a (possibly modified)
        ToolFilter. Hooks run in registration order.

            def log_filter(mode, result):
                print(f"mode={mode} visible={result.visible_names}")
                return result

            client.use(log_filter)
        """
        self._middleware.append(hook)

    def on_suppress(self, callback: SuppressCallback) -> None:
        """Register a callback fired for each tool suppressed during filter().

        Callback receives (tool, mode). Useful for audit logging.
        """
        self._on_suppress.append(callback)

    def on_mode_change(self, callback: ModeChangeCallback) -> None:
        """Register a callback fired when the mode changes between filter() calls.

        Callback receives (old_mode, new_mode). Only fires when mode actually differs.
        """
        self._on_mode_change.append(callback)

    @contextmanager
    def override_mode(self, temporary_mode: float):
        """Context manager for temporary mode overrides.

            with client.override_mode(0.9):
                result = client.filter()  # crisis-level filtering
            # back to normal after the block
        """
        old_source = self._mode_source
        self._mode_source = _StaticMode(temporary_mode)
        try:
            yield self
        finally:
            self._mode_source = old_source

    def filter(self, mode: float | None = None) -> ToolFilter:
        """Filter tools at the current (or overridden) mode level.

        Runs middleware hooks, fires suppress callbacks, and detects mode changes.

        Args:
            mode: Override the mode source for this call only.
                  If None, uses the configured mode source.
        """
        m = mode if mode is not None else self.mode

        # Fire mode-change callbacks
        if self._last_mode is not None and m != self._last_mode:
            for cb in self._on_mode_change:
                cb(self._last_mode, m)
        self._last_mode = m

        result = self._gate.filter(m)

        # Fire suppress callbacks
        for tool in result.suppressed:
            for cb in self._on_suppress:
                cb(tool, m)

        # Run middleware chain
        for hook in self._middleware:
            result = hook(m, result)

        return result

    def export_openai(self, mode: float | None = None) -> list[dict[str, Any]]:
        """Filter and export as OpenAI function-calling tool dicts."""
        return self.filter(mode).to_openai_tools()

    def export_anthropic(self, mode: float | None = None) -> list[dict[str, Any]]:
        """Filter and export as Anthropic tool-use dicts."""
        from gate_sdk.adapters.anthropic import to_anthropic_tools
        result = self.filter(mode)
        return to_anthropic_tools(list(result.visible))

    def authorize(
        self,
        tool_name: str,
        signing_key: str,
        context_id: str = "default",
        mode: float | None = None,
        human_approved: bool = False,
    ) -> AuthorizationEnvelope:
        """Build a signed authorization envelope for a tool.

        Combines filtering + envelope creation in one call. The tool must
        be visible at the current mode — raises ValueError if suppressed.

            envelope = client.authorize("read_file", signing_key="secret")
        """
        m = mode if mode is not None else self.mode
        result = self.filter(m)
        if tool_name not in result.visible_names:
            raise ValueError(
                f"Tool '{tool_name}' is suppressed at mode {m} "
                f"(zone: {result.mode_zone}). Cannot authorize."
            )
        tool = next(t for t in result.visible if t.name == tool_name)
        return build_envelope(
            tool=tool, mode=m, context_id=context_id,
            signing_key=signing_key, human_approved=human_approved,
        )

    def verify(self, envelope: AuthorizationEnvelope, signing_key: str) -> bool:
        """Verify an authorization envelope's signature."""
        return verify_envelope(envelope, signing_key)

    def remove_tool(self, name: str) -> None:
        """Remove a tool by name."""
        self._gate.remove_tool(name)

    @property
    def tools(self) -> list[Tool]:
        """All registered tools."""
        return self._gate.tools
