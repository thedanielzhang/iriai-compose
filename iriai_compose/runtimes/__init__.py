from __future__ import annotations

import asyncio

from iriai_compose.pending import Pending
from iriai_compose.runner import InteractionRuntime


class TerminalInteractionRuntime(InteractionRuntime):
    """Interactive terminal-based interaction runtime."""

    name = "terminal"

    async def resolve(self, pending: Pending) -> str | bool:
        if pending.kind == "approve":
            response = await asyncio.to_thread(
                input, f"\n{pending.prompt}\n[y/n/feedback]: "
            )
            if response.lower() == "y":
                return True
            elif response.lower() == "n":
                return False
            return response
        elif pending.kind == "choose":
            for i, opt in enumerate(pending.options or []):
                print(f"  {i + 1}. {opt}")
            idx_str = await asyncio.to_thread(input, "Choice: ")
            idx = int(idx_str) - 1
            return (pending.options or [])[idx]
        else:  # respond
            return await asyncio.to_thread(
                input, f"\n{pending.prompt}\n> "
            )


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
