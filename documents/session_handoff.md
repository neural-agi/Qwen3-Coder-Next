## Documentation Location

All project documentation is stored in:

documents/

Future coding agents should read:

1. documents/session_handoff.md
2. documents/architecture.md
3. documents/roadmap.md
4. documents/progress.md
5. documents/coding_standards.md



# Session Handoff

## Project

Qwen3-Coder-Next

## Purpose

Qwen3-Coder-Next is a long-term autonomous software engineering agent project inspired by systems such as Codex, Claude Code, Gemini CLI, OpenHands, and Devin.

The goal is to build a modular agent runtime capable of:

* Understanding repositories
* Planning work
* Executing tasks
* Managing state
* Managing artifacts
* Interacting with models through adapters
* Using tools
* Recovering from failures
* Running autonomous software engineering workflows

Current development is focused exclusively on building a clean, testable foundation before any advanced agent capabilities are introduced.

---

## Development Philosophy

Rules that must be followed:

1. Build foundation before intelligence.
2. No shortcuts.
3. No temporary hacks.
4. No unfinished placeholders pretending to be complete systems.
5. Every step must include smoke tests.
6. Existing tests must continue passing.
7. Architecture must remain modular.
8. Prefer composition over tight coupling.
9. Each step should introduce only the minimum functionality required.
10. Maintain clean public APIs.

---

## Current Phase

Part 1: Foundation Layer

Status: In Progress

---

## Completed Steps

### Step 1

Repository skeleton created.

### Step 2

Core contract definitions created.

Implemented:

* Task contracts
* State contracts
* Model contracts
* Artifact contracts

### Step 3

Configuration system created.

Implemented:

* AppSettings
* Environment loading
* Typed configuration
* Configuration smoke tests

### Step 4

Logging infrastructure created.

Implemented:

* Formatter system
* Logger setup
* ApplicationLogger
* File logging
* Console logging
* Logging smoke tests

### Step 5

State management system created.

Implemented:

* StateStore
* StateManager
* State exceptions
* Lifecycle operations
* State smoke tests

### Step 6

Model gateway abstraction created.

Implemented:

* BaseModelAdapter
* StubModelAdapter
* ModelGateway
* Gateway exceptions
* Gateway smoke tests

No real model integrations exist yet.

### Step 7

Orchestration shell created.

Implemented:

* RuntimeContext
* Orchestrator
* Context factory
* Runtime smoke tests

Current orchestrator only logs activity and returns placeholder responses.

### Step 8

Artifact management system created.

Implemented:

* ArtifactStore
* ArtifactManager
* Artifact exceptions
* Artifact lifecycle operations
* Artifact smoke tests

Artifacts are currently in-memory only.

### Step 9

Runtime bootstrap system created.

Implemented:

* RuntimeBootstrap
* Startup lifecycle
* Shutdown lifecycle
* Bootstrap integration tests

Bootstrap now uses the logging system instead of print statements.

### Step 10

Execution skeleton created.

Implemented:

* Executor
* ExecutionResult
* Task lifecycle transitions
* Executor smoke tests

Current execution flow:

PENDING → RUNNING → SUCCEEDED

Executor currently:

* Creates task state
* Updates task state
* Calls stub model gateway
* Calls orchestration shell
* Returns execution result

No real planning or execution logic exists yet.

---

## Current Architecture

Implemented modules:

```text
src/qwen3_coder_next/

bootstrap/
config/
contracts/
logging/
state/
adapters/
runtime/
artifacts/
execution/
```

Core flow:

```text
RuntimeBootstrap
        |
        v
RuntimeContext
        |
        v
Orchestrator
        |
        v
Executor
        |
        +--> StateManager
        |
        +--> ModelGateway
        |
        +--> ArtifactManager
```

---

## Current Test Status

Latest successful run:

```bash
uv run python -m unittest discover -s tests -v
```

Result:

```text
24 tests passed
0 failures
0 errors
```

Foundation remains stable.

---

## Current Model Status

Current adapter:

```text
StubModelAdapter
```

Behavior:

```text
Input  -> ModelGateway
Output -> Fixed ModelResponse
```

No inference.

No API calls.

No external providers.

---

## What Does NOT Exist Yet

The following systems are intentionally not implemented:

* Planning engine
* Memory system
* Vector database
* Tool system
* Repository intelligence
* Code indexing
* Evaluation system
* Reflection system
* Recovery system
* Multi-agent system
* Autonomous workflows
* Real LLM integrations
* OpenAI adapter
* Anthropic adapter
* Qwen adapter
* Gemini adapter

---

## Important Constraints

Do not:

* Rewrite existing architecture
* Remove smoke tests
* Break public APIs
* Introduce external services without roadmap approval
* Add business logic unrelated to the current roadmap step

Do:

* Read architecture.md
* Read roadmap.md
* Read progress.md
* Read coding_standards.md

before making architectural changes.

---

## Next Step

Current target:

```text
Part 1 Foundation
Step 15
```

Before implementing:

1. Read this file.
2. Read architecture.md.
3. Read roadmap.md.
4. Verify all tests pass.
5. Implement only the requested step.
6. Run smoke tests.
7. Update progress.md.
8. Update this file if architecture changes.

---

## Repository Root

```text
Qwen3-Coder-Next/
├── README.md
├── docs/
│   ├── vision.md
│   ├── architecture.md
│   ├── roadmap.md
│   ├── progress.md
│   ├── coding_standards.md
│   └── session_handoff.md
├── src/
├── tests/
├── configs/
├── scripts/
└── docs/
```

---

## Last Known Healthy State

Date: 2026-06-08

Completed Foundation Steps:

```text
1
2
3
4
5
6
7
8
9
10
```

Test Status:

```text
38 passing
0 failing
```

Repository State:

```text
Healthy
Step 14 complete
Ready for Step 15
```
