from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from iriai_compose.tasks import Task
    from iriai_compose.workflow import Feature


class IriaiError(Exception):
    """Base exception for all iriai library errors."""

    pass


class ResolutionError(IriaiError):
    """Actor could not be routed to a runtime."""

    pass


class TaskExecutionError(IriaiError):
    """A task failed during execution.

    Wraps the underlying exception with context about which task,
    actors, phase, and feature were involved. The original exception
    is available via __cause__.
    """

    def __init__(self, *, task: Task, feature: Feature, phase_name: str):
        self.task = task
        self.feature = feature
        self.phase_name = phase_name
        actor_names = self._extract_actor_names(task)
        super().__init__(
            f"Task {type(task).__name__} failed in phase '{phase_name}' "
            f"for feature '{feature.id}' (actors: {actor_names})"
        )

    @staticmethod
    def _extract_actor_names(task: Task) -> str:
        names = []
        for field_name in ["actor", "questioner", "responder", "approver", "chooser"]:
            actor = getattr(task, field_name, None)
            if actor:
                names.append(actor.name)
        return ", ".join(names) or "unknown"
