from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from iriai_compose.runner import AgentRuntime
from iriai_compose.storage import AgentSession, SessionStore

if TYPE_CHECKING:
    from iriai_compose.actors import Role
    from iriai_compose.workflow import Workspace


class ClaudeAgentRuntime(AgentRuntime):
    """Agent runtime backed by the Claude Agent SDK.

    Uses deferred import — the module is importable, but instantiation
    raises a clear error if the SDK is not installed.
    """

    name = "claude"

    def __init__(
        self,
        session_store: SessionStore | None = None,
        on_message: Callable[[Any], None] | None = None,
    ) -> None:
        try:
            import claude_agent_sdk  # noqa: F401
        except ImportError:
            raise ImportError(
                "ClaudeAgentRuntime requires the 'claude-agent-sdk' package. "
                "Install it with: pip install claude-agent-sdk"
            )
        self.session_store = session_store
        self.on_message = on_message

    async def invoke(
        self,
        role: Role,
        prompt: str,
        *,
        output_type: type[BaseModel] | None = None,
        workspace: Workspace | None = None,
        session_key: str | None = None,
    ) -> str | BaseModel:
        from claude_agent_sdk import ClaudeAgentOptions, query
        from claude_agent_sdk.types import ResultMessage

        options = ClaudeAgentOptions(
            system_prompt=role.prompt,
            allowed_tools=role.tools,
            model=role.model or "claude-sonnet-4-6",
            cwd=str(workspace.path) if workspace else None,
        )

        if "setting_sources" in role.metadata:
            options.setting_sources = role.metadata["setting_sources"]

        # Session resumption
        if session_key and self.session_store:
            session = await self.session_store.load(session_key)
            if session and session.session_id:
                options.resume = session.session_id

        if output_type:
            options.output_format = output_type.model_json_schema()

        # Collect the result and let the async generator finish naturally.
        # Breaking out early (via return) triggers GeneratorExit which
        # conflicts with the SDK's internal anyio cancel scope cleanup.
        result_msg: ResultMessage | None = None
        async for msg in query(prompt=prompt, options=options):
            if self.on_message is not None:
                self.on_message(msg)
            if isinstance(msg, ResultMessage):
                result_msg = msg

        if result_msg is None:
            raise RuntimeError("Claude query completed without a result message")

        # Persist session for resumption
        if session_key and self.session_store and result_msg.session_id:
            await self.session_store.save(
                AgentSession(
                    session_key=session_key,
                    session_id=result_msg.session_id,
                )
            )

        if output_type:
            return output_type.model_validate_json(result_msg.result)
        return result_msg.result
