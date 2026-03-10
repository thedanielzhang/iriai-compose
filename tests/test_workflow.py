import pytest
from pathlib import Path

from pydantic import BaseModel

from iriai_compose import Feature, Phase, Workflow, Workspace


def test_workspace_construction():
    ws = Workspace(id="main", path=Path("/tmp/ws"), branch="main")
    assert ws.id == "main"
    assert ws.path == Path("/tmp/ws")
    assert ws.branch == "main"
    assert ws.metadata == {}


def test_workspace_defaults():
    ws = Workspace(id="test", path=Path("."))
    assert ws.branch is None
    assert ws.metadata == {}


def test_feature_construction():
    f = Feature(
        id="f1", name="Feature 1", slug="feature-1",
        workflow_name="pipeline", workspace_id="main",
    )
    assert f.id == "f1"
    assert f.slug == "feature-1"
    assert f.metadata == {}


def test_phase_abc_enforcement():
    with pytest.raises(TypeError):
        Phase()  # type: ignore


def test_workflow_abc_enforcement():
    with pytest.raises(TypeError):
        Workflow()  # type: ignore


def test_concrete_phase():
    class TestPhase(Phase):
        name = "test"

        async def execute(self, runner, feature, state):
            return state

    phase = TestPhase()
    assert phase.name == "test"


def test_concrete_workflow():
    class TestPhase(Phase):
        name = "test"

        async def execute(self, runner, feature, state):
            return state

    class TestWorkflow(Workflow):
        name = "test"

        def build_phases(self):
            return [TestPhase]

    wf = TestWorkflow()
    assert wf.name == "test"
    phases = wf.build_phases()
    assert len(phases) == 1
    assert phases[0] is TestPhase
