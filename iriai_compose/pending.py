from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class Pending(BaseModel):
    """A suspension point where the workflow is waiting on external input."""

    id: str
    feature_id: str
    phase_name: str
    kind: Literal["approve", "choose", "respond"]
    prompt: str
    evidence: Any | None = None
    options: list[str] | None = None
    created_at: datetime
    resolved: bool = False
    response: str | bool | None = None
