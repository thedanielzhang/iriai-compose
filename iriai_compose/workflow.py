from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from iriai_compose.runner import WorkflowRunner


class Workspace(BaseModel):
    """A physical environment where agents execute."""

    id: str
    path: Path
    branch: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Feature(BaseModel):
    """A concrete execution instance binding identity to a workflow and workspace."""

    id: str
    name: str
    slug: str
    workflow_name: str
    workspace_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Phase(ABC):
    """Orchestration unit. Groups tasks with control flow."""

    name: str

    @abstractmethod
    async def execute(
        self, runner: WorkflowRunner, feature: Feature, state: BaseModel
    ) -> BaseModel: ...


class Workflow(ABC):
    """A reusable template. Sequence of Phase types."""

    name: str

    @abstractmethod
    def build_phases(self) -> list[type[Phase]]: ...
