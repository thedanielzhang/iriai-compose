from datetime import datetime

from iriai_compose import Pending


def test_pending_construction():
    p = Pending(
        id="p1",
        feature_id="f1",
        phase_name="planning",
        kind="approve",
        prompt="Approve PRD?",
        created_at=datetime(2024, 1, 1),
    )
    assert p.id == "p1"
    assert p.kind == "approve"
    assert p.resolved is False
    assert p.response is None
    assert p.evidence is None
    assert p.options is None


def test_pending_with_options():
    p = Pending(
        id="p2",
        feature_id="f1",
        phase_name="design",
        kind="choose",
        prompt="Which approach?",
        options=["A", "B", "C"],
        created_at=datetime(2024, 1, 1),
    )
    assert p.options == ["A", "B", "C"]


def test_pending_serialization():
    p = Pending(
        id="p3",
        feature_id="f1",
        phase_name="review",
        kind="respond",
        prompt="Provide feedback",
        evidence={"score": 85},
        created_at=datetime(2024, 1, 1),
        resolved=True,
        response="Looks good",
    )
    data = p.model_dump()
    restored = Pending.model_validate(data)
    assert restored.resolved is True
    assert restored.response == "Looks good"
    assert restored.evidence == {"score": 85}
