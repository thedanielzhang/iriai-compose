"""EchoAgentRuntime — simulated agent for examples.

Returns formatted strings describing what an agent *would* do,
so examples run interactively without the Claude SDK installed.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from iriai_compose import AgentRuntime, Role, Workspace


class EchoAgentRuntime(AgentRuntime):
    """Simulated agent runtime that echoes structured descriptions of what
    a real agent would do, plus constructs placeholder structured outputs."""

    name = "echo"

    def __init__(self, *, interview_rounds: int = 2) -> None:
        self._sessions: dict[str, int] = {}  # session_key -> call count
        self._interview_rounds = interview_rounds  # auto-terminate interviews

    async def invoke(
        self,
        role: Role,
        prompt: str,
        *,
        output_type: type[BaseModel] | None = None,
        workspace: Workspace | None = None,
        session_key: str | None = None,
    ) -> str | BaseModel:
        # Track sessions
        session_info = "new session"
        if session_key:
            count = self._sessions.get(session_key, 0) + 1
            self._sessions[session_key] = count
            if count > 1:
                session_info = f"continuing session (call #{count})"

        # Build description
        tools_str = ", ".join(role.tools) if role.tools else "none"
        prompt_excerpt = prompt[:120] + "..." if len(prompt) > 120 else prompt

        # If structured output requested, construct a placeholder instance
        if output_type is not None:
            return _construct_placeholder(output_type)

        # After enough calls in a session, signal completion so Interview
        # loops terminate naturally (the done predicate typically checks for "DONE")
        done_suffix = ""
        if session_key and self._sessions.get(session_key, 0) > self._interview_rounds:
            done_suffix = "\n  status: DONE — all questions addressed."

        return (
            f"[{role.name}] ({session_info})\n"
            f"  tools: {tools_str}\n"
            f"  prompt: {prompt_excerpt}{done_suffix}"
        )


def _construct_placeholder(model: type[BaseModel]) -> BaseModel:
    """Build a placeholder instance of a Pydantic model with sensible defaults."""
    values: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        if field.default is not None:
            continue  # let Pydantic use its default
        annotation = field.annotation
        if annotation is str or annotation == "str":
            values[name] = f"<placeholder {name}>"
        elif annotation is int or annotation == "int":
            values[name] = 0
        elif annotation is float or annotation == "float":
            values[name] = 0.0
        elif annotation is bool or annotation == "bool":
            values[name] = True
        elif annotation is list or str(annotation).startswith("list"):
            values[name] = []
    return model.model_construct(**values)
