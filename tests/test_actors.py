from iriai_compose import Actor, AgentActor, InteractionActor, Role


def test_role_defaults():
    role = Role(name="pm", prompt="You are a PM.")
    assert role.tools == []
    assert role.model is None
    assert role.metadata == {}


def test_role_with_all_fields():
    role = Role(
        name="architect",
        prompt="You are an architect.",
        tools=["Read", "Bash"],
        model="claude-opus-4-6",
        metadata={"setting_sources": ["project"]},
    )
    assert role.tools == ["Read", "Bash"]
    assert role.model == "claude-opus-4-6"
    assert role.metadata["setting_sources"] == ["project"]


def test_actor_base():
    actor = Actor(name="test")
    assert actor.name == "test"


def test_agent_actor_defaults():
    role = Role(name="pm", prompt="PM")
    actor = AgentActor(name="pm", role=role)
    assert actor.context_keys == []
    assert actor.persistent is True


def test_agent_actor_with_context():
    role = Role(name="pm", prompt="PM")
    actor = AgentActor(
        name="pm", role=role, context_keys=["project", "prd"], persistent=False
    )
    assert actor.context_keys == ["project", "prd"]
    assert actor.persistent is False


def test_interaction_actor():
    actor = InteractionActor(name="user", resolver="human.slack")
    assert actor.resolver == "human.slack"


def test_actor_serialization():
    role = Role(name="pm", prompt="PM", tools=["Read"])
    actor = AgentActor(name="pm", role=role, context_keys=["project"])
    data = actor.model_dump()
    restored = AgentActor.model_validate(data)
    assert restored.name == "pm"
    assert restored.role.name == "pm"
    assert restored.context_keys == ["project"]


def test_interaction_actor_serialization():
    actor = InteractionActor(name="user", resolver="human.terminal")
    data = actor.model_dump()
    restored = InteractionActor.model_validate(data)
    assert restored.resolver == "human.terminal"
