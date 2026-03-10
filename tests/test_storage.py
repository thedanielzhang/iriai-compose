import pytest
from pathlib import Path

from iriai_compose import (
    AgentSession,
    DefaultContextProvider,
    Feature,
    InMemoryArtifactStore,
    InMemorySessionStore,
)


@pytest.fixture
def feature():
    return Feature(
        id="f1", name="F1", slug="f1", workflow_name="test", workspace_id="main"
    )


@pytest.fixture
def feature2():
    return Feature(
        id="f2", name="F2", slug="f2", workflow_name="test", workspace_id="main"
    )


async def test_artifact_put_get(feature):
    store = InMemoryArtifactStore()
    await store.put("prd", {"content": "PRD data"}, feature=feature)
    result = await store.get("prd", feature=feature)
    assert result == {"content": "PRD data"}


async def test_artifact_missing_key(feature):
    store = InMemoryArtifactStore()
    result = await store.get("nonexistent", feature=feature)
    assert result is None


async def test_artifact_feature_isolation(feature, feature2):
    store = InMemoryArtifactStore()
    await store.put("prd", "f1-prd", feature=feature)
    await store.put("prd", "f2-prd", feature=feature2)
    assert await store.get("prd", feature=feature) == "f1-prd"
    assert await store.get("prd", feature=feature2) == "f2-prd"


async def test_artifact_overwrite(feature):
    store = InMemoryArtifactStore()
    await store.put("prd", "v1", feature=feature)
    await store.put("prd", "v2", feature=feature)
    assert await store.get("prd", feature=feature) == "v2"


async def test_session_store():
    store = InMemorySessionStore()
    session = AgentSession(session_key="pm:f1", session_id="s123")
    await store.save(session)
    loaded = await store.load("pm:f1")
    assert loaded is not None
    assert loaded.session_id == "s123"


async def test_session_store_missing():
    store = InMemorySessionStore()
    assert await store.load("nonexistent") is None


async def test_context_provider_from_artifacts(feature):
    store = InMemoryArtifactStore()
    await store.put("prd", "The PRD content", feature=feature)
    await store.put("design", "The design content", feature=feature)
    provider = DefaultContextProvider(artifacts=store)
    result = await provider.resolve(["prd", "design"], feature=feature)
    assert "## prd" in result
    assert "The PRD content" in result
    assert "## design" in result
    assert "The design content" in result


async def test_context_provider_missing_keys_skipped(feature):
    store = InMemoryArtifactStore()
    await store.put("prd", "PRD", feature=feature)
    provider = DefaultContextProvider(artifacts=store)
    result = await provider.resolve(["prd", "nonexistent"], feature=feature)
    assert "## prd" in result
    assert "nonexistent" not in result


async def test_context_provider_static_files(feature, tmp_path):
    store = InMemoryArtifactStore()
    static_file = tmp_path / "project.md"
    static_file.write_text("Project description")
    provider = DefaultContextProvider(
        artifacts=store, static_files={"project": static_file}
    )
    result = await provider.resolve(["project"], feature=feature)
    assert "## project" in result
    assert "Project description" in result


async def test_context_provider_empty_keys(feature):
    store = InMemoryArtifactStore()
    provider = DefaultContextProvider(artifacts=store)
    result = await provider.resolve([], feature=feature)
    assert result == ""
