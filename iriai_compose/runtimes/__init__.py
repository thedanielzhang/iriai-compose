from __future__ import annotations

from iriai_compose.pending import Pending
from iriai_compose.runner import InteractionRuntime
from iriai_compose.runtimes.terminal import TerminalInteractionRuntime


class AutoApproveRuntime(InteractionRuntime):
    """Auto-approves all interaction requests."""

    name = "auto"

    async def resolve(self, pending: Pending) -> str | bool:
        if pending.kind == "approve":
            return True
        if pending.kind == "choose":
            return (pending.options or [""])[0]
        return "auto-approved"


__all__ = ["TerminalInteractionRuntime", "AutoApproveRuntime"]
