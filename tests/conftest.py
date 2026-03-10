from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from iriai_compose import (
    AgentActor,
    AgentRuntime,
    Feature,
    InteractionActor,
    InteractionRuntime,
    Role,
    Workspace,
)
from iriai_compose.pending import Pending


class MockAgentRuntime(AgentRuntime):
    """Configurable: returns canned responses or calls a handler function."""

    name = "mock"

    def __init__(
        self,
        response: str | BaseModel | None = None,
        handler: Any = None,
    ) -> None:
        self._response = response or "mock response"
        self._handler = handler
        self.calls: list[dict[str, Any]] = []

    async def invoke(
        self,
        role: Role,
        prompt: str,
        *,
        output_type: type[BaseModel] | None = None,
        workspace: Workspace | None = None,
        session_key: str | None = None,
    ) -> str | BaseModel:
        call = {
            "role": role,
            "prompt": prompt,
            "output_type": output_type,
            "workspace": workspace,
            "session_key": session_key,
        }
        self.calls.append(call)
        if self._handler:
            return self._handler(call)
        return self._response


class MockInteractionRuntime(InteractionRuntime):
    """Returns canned responses per kind."""

    name = "mock"

    def __init__(
        self,
        approve: bool | str = True,
        choose: str = "",
        respond: str = "mock input",
    ) -> None:
        self._approve = approve
        self._choose = choose
        self._respond = respond
        self.calls: list[Pending] = []

    async def resolve(self, pending: Pending) -> str | bool:
        self.calls.append(pending)
        if pending.kind == "approve":
            return self._approve
        if pending.kind == "choose":
            return self._choose or (pending.options or [""])[0]
        return self._respond


@pytest.fixture
def pm_role() -> Role:
    return Role(
        name="pm",
        prompt="You are a PM.",
        tools=["Read", "Glob"],
    )


@pytest.fixture
def architect_role() -> Role:
    return Role(
        name="architect",
        prompt="You are an architect.",
        tools=["Read", "Bash"],
        model="claude-opus-4-6",
    )


@pytest.fixture
def agent_actor(pm_role: Role) -> AgentActor:
    return AgentActor(
        name="pm",
        role=pm_role,
        context_keys=["project"],
    )


@pytest.fixture
def interaction_actor() -> InteractionActor:
    return InteractionActor(name="user", resolver="human.slack")


@pytest.fixture
def feature() -> Feature:
    return Feature(
        id="test-feature",
        name="Test Feature",
        slug="test-feature",
        workflow_name="test",
        workspace_id="main",
    )


@pytest.fixture
def workspace() -> Workspace:
    return Workspace(
        id="main",
        path=Path("/tmp/test-workspace"),
        branch="main",
    )
