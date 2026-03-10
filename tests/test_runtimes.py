from datetime import datetime
from unittest.mock import patch

import pytest

from iriai_compose.pending import Pending
from iriai_compose.runtimes import AutoApproveRuntime, TerminalInteractionRuntime


@pytest.fixture
def approve_pending():
    return Pending(
        id="p1",
        feature_id="f1",
        phase_name="test",
        kind="approve",
        prompt="Approve?",
        created_at=datetime.now(),
    )


@pytest.fixture
def choose_pending():
    return Pending(
        id="p2",
        feature_id="f1",
        phase_name="test",
        kind="choose",
        prompt="Pick one",
        options=["A", "B", "C"],
        created_at=datetime.now(),
    )


@pytest.fixture
def respond_pending():
    return Pending(
        id="p3",
        feature_id="f1",
        phase_name="test",
        kind="respond",
        prompt="Tell me more",
        created_at=datetime.now(),
    )


# --- AutoApproveRuntime ---

async def test_auto_approve_approve(approve_pending):
    rt = AutoApproveRuntime()
    result = await rt.resolve(approve_pending)
    assert result is True


async def test_auto_approve_choose(choose_pending):
    rt = AutoApproveRuntime()
    result = await rt.resolve(choose_pending)
    assert result == "A"


async def test_auto_approve_respond(respond_pending):
    rt = AutoApproveRuntime()
    result = await rt.resolve(respond_pending)
    assert result == "auto-approved"


# --- TerminalInteractionRuntime ---

async def test_terminal_approve_yes(approve_pending):
    rt = TerminalInteractionRuntime()
    with patch("iriai_compose.runtimes.asyncio.to_thread", return_value="y"):
        result = await rt.resolve(approve_pending)
    assert result is True


async def test_terminal_approve_no(approve_pending):
    rt = TerminalInteractionRuntime()
    with patch("iriai_compose.runtimes.asyncio.to_thread", return_value="n"):
        result = await rt.resolve(approve_pending)
    assert result is False


async def test_terminal_approve_feedback(approve_pending):
    rt = TerminalInteractionRuntime()
    with patch(
        "iriai_compose.runtimes.asyncio.to_thread", return_value="needs changes"
    ):
        result = await rt.resolve(approve_pending)
    assert result == "needs changes"


async def test_terminal_choose(choose_pending):
    rt = TerminalInteractionRuntime()
    with patch("iriai_compose.runtimes.asyncio.to_thread", return_value="2"):
        result = await rt.resolve(choose_pending)
    assert result == "B"


async def test_terminal_respond(respond_pending):
    rt = TerminalInteractionRuntime()
    with patch(
        "iriai_compose.runtimes.asyncio.to_thread", return_value="my feedback"
    ):
        result = await rt.resolve(respond_pending)
    assert result == "my feedback"


# --- Claude deferred import ---

def test_claude_runtime_import_error():
    try:
        import claude_agent_sdk  # noqa: F401
        pytest.skip("claude-agent-sdk is installed")
    except ImportError:
        pass
    with pytest.raises(ImportError, match="claude-agent-sdk"):
        from iriai_compose.runtimes.claude import ClaudeAgentRuntime
        ClaudeAgentRuntime()
