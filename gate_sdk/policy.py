"""Policy integration contract — how Layer 2 policy engines consume the SDK.

gate-policy (Layer 2) needs to:
1. Define rules that map conditions to mode adjustments
2. Feed those adjustments into the SDK's mode source
3. Optionally add middleware that enforces policy constraints

This module defines the protocols that gate-policy should implement.
NOT WIRED YET — defines the contract only.
"""
from __future__ import annotations

from typing import Any, Protocol

from gatekeeper import ToolFilter


class PolicyEngine(Protocol):
    """Protocol for policy engines that feed into gate-sdk.

    A policy engine evaluates context (user role, time of day,
    risk signals) and produces a mode adjustment.
    """

    def evaluate(self, context: dict[str, Any]) -> float:
        """Evaluate context and return a mode float in [0.0, 1.0].

        The returned mode is fed into GateClient as a mode source
        or used to override mode per-request.
        """
        ...

    def name(self) -> str:
        """Human-readable policy name for audit logging."""
        ...


class PolicyMiddleware:
    """Middleware adapter that applies a PolicyEngine to every filter() call.

    Usage:
        policy = MyCompliancePolicy()
        middleware = PolicyMiddleware(policy)
        client.use(middleware.hook)

    The middleware evaluates the policy and adjusts the filter result
    if the policy demands a stricter mode than what was requested.
    """

    def __init__(self, engine: PolicyEngine, context: dict[str, Any] | None = None) -> None:
        self._engine = engine
        self._context = context or {}

    def set_context(self, context: dict[str, Any]) -> None:
        self._context = context

    def hook(self, mode: float, result: ToolFilter) -> ToolFilter:
        """Middleware hook — re-filters if policy demands stricter mode.

        If the policy's evaluated mode is higher than the requested mode,
        the result is re-filtered at the stricter level. This ensures
        policy always wins over the ambient mode signal.
        """
        from gatekeeper.core import is_suppressed, T_DOWN, T_UP

        policy_mode = self._engine.evaluate(self._context)
        if policy_mode <= mode:
            return result

        # Policy demands stricter filtering — re-partition visible tools
        all_tools = result.visible + result.suppressed
        new_visible = []
        new_suppressed = []
        for t in all_tools:
            if is_suppressed(t.execution_class, policy_mode):
                new_suppressed.append(t)
            else:
                new_visible.append(t)

        zone = "normal" if policy_mode <= T_DOWN else ("elevated" if policy_mode <= T_UP else "crisis")

        return ToolFilter(
            visible=tuple(new_visible),
            suppressed=tuple(new_suppressed),
            mode=policy_mode,
            mode_zone=zone,
            thresholds=result.thresholds,
        )
