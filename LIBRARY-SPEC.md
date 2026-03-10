# iriai-sdk: Multi-Agent Workflow Library Specification

This document defines the core library model for `iriai-sdk`.

It is intentionally separate from the earlier `SPEC.md`.

The goal of this spec is to describe the library layer only:

- workflow definitions
- task definitions
- task input/output contracts
- storage abstractions
- interaction abstractions
- runtime adapter boundaries

Durability, replay, scheduling, crash recovery, queues, background workers, and UI delivery are application-layer concerns.

---

## Purpose

`iriai-sdk` is a library for composing multi-agent workflows.

It should support workflows like `iriai-build`, but it should not itself be a full orchestration service.

The library is responsible for representing:

- workflows
- phases
- tasks
- roles
- workspaces
- artifacts
- interactions
- runtime adapter boundaries

The application using the library is responsible for:

- persistence
- retries
- recovery
- eventing
- transport wiring
- long-running process management

---

## Design Principles

1. `Workflow`, `Phase`, and `Task` are definition-layer concepts.
2. A `Task` is atomic and is either agent-driven or interaction-driven.
3. A `Phase` owns orchestration: sequencing, branching, loops, parallel fan-out, and child workflow coordination.
4. A `WorkflowRunner` coordinates execution and dispatches tasks.
5. Agent SDK specifics belong in runtime adapters, not in the core library model.
6. Interaction resolution should not assume a human; it may be resolved by a person, an agent, or an automated policy.
7. Storage is abstracted behind contracts so applications can use memory, filesystem, SQL, or mixed backends.

---

## Conceptual Categories

The core model is split into these categories:

### 1. Workflow Structure

- `Workflow`
- `Phase`
- `Task`

### 2. Task Data Contracts

- `TaskInput`
- `TaskOutput`
- specialized input/output models for built-in task types

### 3. Agent Model

- `Role`
- `AgentProfile`
- `AgentSession`
- `AgentResult`

### 4. Runtime Adapter Layer

- `AgentRuntime`
- `InteractionRuntime`
- optional `MessageTransport`

### 5. Data and Storage

- `ArtifactStore`
- `SessionStore`
- `MessageStore`
- `ContextProvider`

### 6. Execution Environment

- `Workspace`
- `Feature`

### 7. Coordination Layer

- `WorkflowRunner`

---

## Core Definitions

### State Models

The core library uses explicit structured state models.

Applications may define richer state types by subclassing these.

```python
from pydantic import BaseModel, Field
from typing import Any


class WorkflowState(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class PhaseState(WorkflowState):
    pass
```

### Workflow

A `Workflow` is a reusable template made of phases.

It defines the overall structure of a process, but it does not itself execute SDK calls.

```python
from abc import ABC, abstractmethod


class Workflow(ABC):
    name: str
    phase_types: list[type["Phase"]]

    @abstractmethod
    def build_phases(self) -> list[type["Phase"]]:
        """Return the ordered phase definitions for this workflow."""
        ...
```

Rules:

- A workflow is reusable.
- A workflow is definition-only.
- A workflow may be static or dynamic through `build_phases()`.

### Phase

A `Phase` is an orchestration unit inside a workflow.

It owns:

- sequencing
- loops
- branching
- retries
- parallel branches
- child workflow invocation

It does not itself make Claude/Codex SDK calls directly. It uses a `WorkflowRunner`.

```python
class Phase(ABC):
    name: str

    @abstractmethod
    async def execute(self, runner: "WorkflowRunner", state: PhaseState) -> PhaseState:
        """Advance phase state by dispatching tasks and coordinating results."""
        ...
```

Rules:

- A phase may contain many tasks.
- A phase may call child workflows.
- A phase may coordinate parallel work.
- A phase is not an atomic unit of execution.

### Task

A `Task` is the atomic unit of work.

Every task is exactly one thing and must be one of:

- `agent`
- `interaction`

Examples:

- ask one agent for one result
- request one approval
- request one free-form response
- request one choice from a list

`Parallel` and `ChildWorkflow` are not tasks. They are orchestration behaviors at the phase/workflow layer.

```python
from pydantic import BaseModel
from typing import ClassVar, Literal


class Task(BaseModel):
    id: str
    kind: Literal["agent", "interaction"]
    name: str | None = None

    input_model: ClassVar[type["TaskInput"]]
    output_model: ClassVar[type["TaskOutput"]]
```

Rules:

- A task is definition-only.
- A task does not execute itself.
- A task declares its input and output contracts.
- The runner dispatches the task to the correct runtime.

---

## Task Input and Output Contracts

Task I/O is the most important stable contract in the library.

### Base Models

All task inputs and outputs must be structured, serializable models.

```python
from pydantic import BaseModel, Field
from typing import Any, Literal


class TaskInput(BaseModel):
    workspace_id: str | None = None
    thread_id: str | None = None
    context_keys: list[str] = Field(default_factory=list)
    artifact_refs: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskOutput(BaseModel):
    status: Literal["completed", "pending", "failed"] = "completed"
    artifact_refs: dict[str, str] = Field(default_factory=dict)
    message_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Rules:

- Inputs and outputs must be serializable.
- Large artifacts should be stored through stores and referenced by key.
- Runtime handles must not appear in task inputs or outputs.
- Integration metadata belongs in `metadata`, not in ad hoc fields.

### Built-in Agent Task Contracts

```python
class AskTaskInput(TaskInput):
    role: str
    runtime: str
    prompt: str
    session_key: str | None = None
    profile: dict[str, Any] = Field(default_factory=dict)


class AskTaskOutput(TaskOutput):
    content: str
    structured: dict[str, Any] | None = None
    session_key: str | None = None
```

```python
class AskTask(Task):
    kind: Literal["agent"] = "agent"
    input_model = AskTaskInput
    output_model = AskTaskOutput
```

### Built-in Interaction Task Contracts

`InteractionTask` is the abstraction for approval, choice, and free-form response.

It does not assume a human. The resolver may be:

- terminal-human
- slack-human
- desktop-human
- reviewer-agent
- auto-approver

```python
class InteractionTaskInput(TaskInput):
    resolver: str
    title: str
    prompt: str
    evidence_refs: list[str] = Field(default_factory=list)


class ApprovalTaskInput(InteractionTaskInput):
    pass


class ApprovalTaskOutput(TaskOutput):
    approved: bool
    comment: str | None = None


class ChoiceTaskInput(InteractionTaskInput):
    options: list[str]


class ChoiceTaskOutput(TaskOutput):
    selection: str


class ResponseTaskInput(InteractionTaskInput):
    pass


class ResponseTaskOutput(TaskOutput):
    content: str
```

```python
class ApprovalTask(Task):
    kind: Literal["interaction"] = "interaction"
    input_model = ApprovalTaskInput
    output_model = ApprovalTaskOutput


class ChoiceTask(Task):
    kind: Literal["interaction"] = "interaction"
    input_model = ChoiceTaskInput
    output_model = ChoiceTaskOutput


class ResponseTask(Task):
    kind: Literal["interaction"] = "interaction"
    input_model = ResponseTaskInput
    output_model = ResponseTaskOutput
```

### Task I/O Management Rules

Task input and output should be managed like this:

1. A phase creates a task definition and a typed input payload.
2. The runner validates that the input matches `task.input_model`.
3. The runner dispatches the task to the correct runtime.
4. The runtime returns raw result data.
5. The runner normalizes that raw result into `task.output_model`.
6. The phase decides what to do with the result next.

This keeps:

- task definitions stable
- runtime adapters replaceable
- storage independent from execution

---

## Agent Model

The core library needs a runtime-neutral agent model.

### Role

A `Role` defines expertise and perspective only.

```python
class Role(BaseModel):
    name: str
    prompt: str
```

### AgentProfile

An `AgentProfile` defines execution settings the runtime adapter may need.

It is runtime-neutral at the core layer.

```python
class AgentProfile(BaseModel):
    runtime: str
    model: str | None = None
    tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Examples:

- Claude adapter may use `model`, `tools`, and `setting_sources` in `metadata`
- Codex adapter may use a different subset of fields

### AgentSession

An `AgentSession` represents runtime-specific continuity.

```python
class AgentSession(BaseModel):
    runtime: str
    session_key: str
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### AgentResult

```python
class AgentResult(BaseModel):
    content: str
    structured: dict[str, Any] | None = None
    session: AgentSession | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

---

## Runtime Adapter Layer

The core library should sit above runtime adapters.

This is how the library stays reusable across Claude SDK, Codex SDK, and future integrations.

### AgentRuntime

An `AgentRuntime` executes agent tasks.

```python
class AgentRuntime(ABC):
    name: str

    @abstractmethod
    async def execute(
        self,
        task: AskTask,
        input: AskTaskInput,
        runner: "WorkflowRunner",
    ) -> AskTaskOutput:
        ...
```

The Claude adapter is the first implementation target, but it is not the core abstraction.

### InteractionRuntime

An `InteractionRuntime` executes interaction tasks.

This may be backed by:

- a human in a terminal
- Slack
- a desktop UI
- another agent
- an auto-policy

```python
class InteractionRuntime(ABC):
    name: str

    @abstractmethod
    async def execute(
        self,
        task: Task,
        input: InteractionTaskInput,
        runner: "WorkflowRunner",
    ) -> TaskOutput:
        ...
```

### MessageTransport

`MessageTransport` is optional and sits below an `InteractionRuntime`.

It is useful when an interaction runtime sends or receives messages through an external channel.

```python
class MessageTransport(ABC):
    @abstractmethod
    async def send(self, thread_id: str, content: str) -> str:
        """Send a message and return a transport-level message reference."""
        ...

    @abstractmethod
    async def receive(self, request_id: str) -> str:
        """Receive a reply for a previously-issued request."""
        ...
```

The core library should not require a transport, but it should be easy for applications to use one.

---

## Data and Storage

The library must expose storage contracts, but not enforce one storage backend.

### ArtifactStore

An `ArtifactStore` persists workflow outputs and reusable documents.

```python
class ArtifactStore(ABC):
    @abstractmethod
    async def get(self, key: str) -> BaseModel | str | None:
        ...

    @abstractmethod
    async def put(self, key: str, value: BaseModel | str) -> None:
        ...
```

Typical artifacts:

- scoped request
- PRD
- design package
- architecture package
- review findings
- final implementation summary

### SessionStore

A `SessionStore` persists runtime session data if the application wants continuity.

```python
class SessionStore(ABC):
    @abstractmethod
    async def load(self, session_key: str) -> AgentSession | None:
        ...

    @abstractmethod
    async def save(self, session: AgentSession) -> None:
        ...
```

### MessageStore

A `MessageStore` persists message history if the application needs it.

```python
class Message(BaseModel):
    thread_id: str
    sender: Literal["human", "agent", "system", "workflow"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageStore(ABC):
    @abstractmethod
    async def append(self, message: Message) -> None:
        ...

    @abstractmethod
    async def list(self, thread_id: str) -> list[Message]:
        ...
```

### ContextProvider

A `ContextProvider` converts stored data into prompt-ready context for agent runtimes.

```python
class ContextProvider(ABC):
    @abstractmethod
    async def resolve(self, keys: list[str], *, feature: "Feature") -> str:
        ...
```

This is intentionally separate from artifact persistence.

---

## Execution Environment

### Workspace

A `Workspace` is the physical place where code and files live.

This is a real execution environment for agents.

It is not a run-state store.

```python
from pathlib import Path


class Workspace(BaseModel):
    id: str
    path: Path
    branch: str | None = None
    artifacts_dir: Path | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

Examples:

- shared repo root
- git worktree
- temp directory
- feature branch workspace
- team-specific workspace

### Feature

A `Feature` is a concrete execution instance that binds together the important environment-level objects.

```python
class Feature(BaseModel):
    id: str
    name: str
    workflow_name: str
    workspace_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

The application may expand this significantly, but the core library only needs the concept.

---

## Coordination Layer

### WorkflowRunner

`WorkflowRunner` is the coordinator and dispatcher.

It is the layer that phases talk to.

It is responsible for:

- validating task inputs
- dispatching tasks
- invoking child workflows
- coordinating parallel branches
- exposing stores and workspace lookup to phases

It is not the Claude/Codex adapter itself.

```python
class WorkflowRunner(ABC):
    artifacts: ArtifactStore
    sessions: SessionStore | None
    messages: MessageStore | None
    context_provider: ContextProvider

    @abstractmethod
    async def execute_task(self, task: Task, input: TaskInput) -> TaskOutput:
        ...

    @abstractmethod
    async def execute_workflow(self, workflow: Workflow, state: BaseModel) -> BaseModel:
        ...

    @abstractmethod
    async def execute_child(
        self,
        workflow: Workflow,
        state: BaseModel,
        *,
        workspace_id: str | None = None,
    ) -> BaseModel:
        ...

    @abstractmethod
    async def execute_parallel(
        self,
        children: list[tuple[Workflow, BaseModel, str | None]],
    ) -> list[BaseModel]:
        ...

    @abstractmethod
    def get_workspace(self, workspace_id: str | None) -> Workspace | None:
        ...
```

### Default Dispatch Logic

The runner should route tasks by type.

```python
class DefaultWorkflowRunner(WorkflowRunner):
    def __init__(
        self,
        *,
        agent_runtimes: dict[str, AgentRuntime],
        interaction_runtimes: dict[str, InteractionRuntime],
        artifacts: ArtifactStore,
        sessions: SessionStore | None = None,
        messages: MessageStore | None = None,
        context_provider: ContextProvider,
    ):
        ...

    async def execute_task(self, task: Task, input: TaskInput) -> TaskOutput:
        if isinstance(task, AskTask):
            runtime = self.agent_runtimes[input.runtime]
            return await runtime.execute(task, input, self)

        if isinstance(task, (ApprovalTask, ChoiceTask, ResponseTask)):
            runtime = self.interaction_runtimes[input.resolver]
            return await runtime.execute(task, input, self)

        raise TypeError(f"Unsupported task type: {type(task).__name__}")
```

This keeps the core model clean:

- phases define intent
- runner coordinates
- runtimes execute

---

## Phase-Level Orchestration

Parallel and child workflows belong to the phase/workflow layer.

They are not tasks.

### ParallelPhase

`ParallelPhase` is a specialized phase that coordinates multiple child workflows or parallel branches.

```python
class ParallelPhase(Phase):
    @abstractmethod
    async def build_children(
        self,
        runner: WorkflowRunner,
        state: BaseModel,
    ) -> list[tuple[Workflow, BaseModel, str | None]]:
        ...

    async def execute(self, runner: WorkflowRunner, state: BaseModel) -> BaseModel:
        results = await runner.execute_parallel(await self.build_children(runner, state))
        return self.merge_results(state, results)

    @abstractmethod
    def merge_results(self, state: BaseModel, results: list[BaseModel]) -> BaseModel:
        ...
```

### Child Workflow Invocation

Any phase may invoke a child workflow through the runner:

```python
result = await runner.execute_child(
    child_workflow,
    child_state,
    workspace_id="team-1",
)
```

This is how workflows like `iriai-build` should represent:

- feature implementation subflows
- team-level orchestration
- review lanes

---

## Example: `iriai-build` In This Model

This example mirrors the real `iriai-build` flow at a conceptual level:

- scoping
- PM
- PM review
- design
- design review
- architecture
- architecture review
- plan compiler loop
- plan approval
- implementation child workflow
- completion

```python
class BuildFeatureState(BaseModel):
    slug: str
    description: str
    thread_id: str

    scoped_key: str | None = None
    prd_key: str | None = None
    design_key: str | None = None
    architecture_key: str | None = None
    implementation_key: str | None = None
```

```python
class BuildFeatureWorkflow(Workflow):
    name = "build-feature"
    phase_types = [
        ScopingPhase,
        PMPhase,
        PMReviewPhase,
        DesignPhase,
        DesignReviewPhase,
        ArchitecturePhase,
        ArchitectureReviewPhase,
        PlanCompilerPhase,
        PlanApprovalPhase,
        ImplementationPhase,
        CompletionPhase,
    ]

    def build_phases(self) -> list[type[Phase]]:
        return self.phase_types
```

```python
class PMPhase(Phase):
    name = "pm"

    async def execute(self, runner: WorkflowRunner, state: BuildFeatureState) -> BuildFeatureState:
        output = await runner.execute_task(
            AskTask(id="planning.pm.prd"),
            AskTaskInput(
                role="pm",
                runtime="claude",
                prompt="Produce a PRD for this scoped feature.",
                context_keys=["project", "scoped-feature"],
                workspace_id="feature-root",
                session_key=f"pm:{state.slug}",
            ),
        )
        await runner.artifacts.put("prd", output.structured or output.content)
        state.prd_key = "prd"
        return state
```

```python
class PMReviewPhase(Phase):
    name = "pm-review"

    async def execute(self, runner: WorkflowRunner, state: BuildFeatureState) -> BuildFeatureState:
        decision = await runner.execute_task(
            ApprovalTask(id="planning.pm.review"),
            ApprovalTaskInput(
                resolver="human.slack",
                title="Review PRD",
                prompt="Approve the PRD before design begins.",
                evidence_refs=["prd"],
                thread_id=state.thread_id,
            ),
        )
        if not decision.approved:
            revised = await runner.execute_task(
                AskTask(id="planning.pm.revise"),
                AskTaskInput(
                    role="pm",
                    runtime="claude",
                    prompt=f"Revise the PRD using this feedback:\n\n{decision.comment or ''}",
                    context_keys=["project", "prd"],
                    workspace_id="feature-root",
                    session_key=f"pm:{state.slug}",
                ),
            )
            await runner.artifacts.put("prd", revised.structured or revised.content)
        return state
```

```python
class PlanCompilerPhase(Phase):
    name = "plan-compiler"

    async def execute(self, runner: WorkflowRunner, state: BuildFeatureState) -> BuildFeatureState:
        attempt = 1
        while True:
            verdict = await runner.execute_task(
                AskTask(id=f"planning.plan-compiler.validate-{attempt}"),
                AskTaskInput(
                    role="plan-compiler",
                    runtime="claude",
                    prompt="Validate the current architecture and plan. Return PASS or FAIL with feedback.",
                    context_keys=["project", "prd", "design", "architecture"],
                    workspace_id="feature-root",
                    session_key=f"plan-compiler:{state.slug}",
                ),
            )
            data = verdict.structured or {}
            if data.get("passed"):
                return state

            revised = await runner.execute_task(
                AskTask(id=f"planning.architect.revise-{attempt}"),
                AskTaskInput(
                    role="architect",
                    runtime="claude",
                    prompt=f"Revise the architecture using this feedback:\n\n{data.get('feedback', '')}",
                    context_keys=["project", "prd", "design", "architecture"],
                    workspace_id="feature-root",
                    session_key=f"architect:{state.slug}",
                ),
            )
            await runner.artifacts.put("architecture", revised.structured or revised.content)
            attempt += 1
```

```python
class ImplementationPhase(Phase):
    name = "implementation"

    async def execute(self, runner: WorkflowRunner, state: BuildFeatureState) -> BuildFeatureState:
        child_state = BuildFeatureState(
            slug=state.slug,
            description=state.description,
            thread_id=state.thread_id,
            architecture_key=state.architecture_key,
        )
        result = await runner.execute_child(
            FeatureImplementationWorkflow(),
            child_state,
            workspace_id="feature-worktree",
        )
        state.implementation_key = "implementation"
        await runner.artifacts.put("implementation", result.model_dump())
        return state
```

The implementation child workflow can then fan out into team workflows through a `ParallelPhase`.

This maps naturally onto the way `iriai-build` does:

- feature lead orchestration
- team fan-out
- review agents
- gate approvals

without turning those concepts into atomic tasks.

---

## What Is In Core vs Application

### Core Library

The core library should define:

- `Workflow`
- `Phase`
- `Task`
- task input/output contracts
- `Role`
- `AgentProfile`
- `AgentRuntime`
- `InteractionRuntime`
- `ArtifactStore`
- `SessionStore`
- `MessageStore`
- `ContextProvider`
- `Workspace`
- `WorkflowRunner`

### Application Layer

The application should decide:

- whether to persist anything
- where to store artifacts, sessions, and messages
- how to do retries
- how to do recovery
- how to schedule long-running work
- how to present interactions to users
- how to route interactions to humans, agents, or automation

---

## Summary

This spec defines `iriai-sdk` as a thin but structured workflow library.

The core mental model is:

- `Workflow`, `Phase`, `Task` are definitions
- `WorkflowRunner` coordinates and dispatches
- `AgentRuntime` executes agent tasks
- `InteractionRuntime` executes approval/choice/response tasks
- `MessageTransport` is an optional lower-level messaging primitive
- storage is abstracted behind interfaces
- workspaces represent physical file/code environments

This keeps the library:

- reusable
- adapter-friendly
- storage-agnostic
- compatible with Claude SDK first
- extensible to Codex SDK and other runtimes later
