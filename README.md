# Qwen3-Coder-Next

Qwen3-Coder-Next is an open-source, local-first coding agent framework designed to provide Codex-like project assistance while running primarily on user-controlled infrastructure.

The project is currently in the Foundation Phase, where the focus is on building a clean, modular, and testable architecture before introducing planning systems, memory, repository intelligence, tool execution, and autonomous coding workflows.


---

## Current Status

### Part 1: Foundation

Completed:

* ✅ Step 1: Repository Skeleton
* ✅ Step 2: Core Contracts
* ✅ Step 3: Configuration System
* ✅ Step 4: Logging Infrastructure
* ✅ Step 5: In-Memory State Management
* ✅ Step 6: Model Gateway Abstraction
* ✅ Step 7: Runtime Orchestration Shell
* ✅ Step 8: Artifact Management
* ✅ Step 9: Runtime Bootstrap Layer
* ✅ Step 10: Execution Framework

Current test status:

```text
24 tests passed
```

---

## Project Goals

Qwen3-Coder-Next aims to become a modular coding-agent platform capable of:

* Repository understanding
* Planning and task decomposition
* Memory and context management
* Tool execution
* Artifact generation
* Autonomous coding workflows
* Local-first operation
* Support for multiple model backends

The project is intentionally being built from the foundation upward to ensure maintainability, testability, and extensibility.

---

## Current Architecture

### Foundation Layer

#### Contracts

Strongly typed immutable contracts used across the system.

Examples:

* TaskRequest
* TaskResult
* TaskState
* ModelRequest
* ModelResponse
* ArtifactRecord

#### Configuration

Centralized application settings with:

* Environment support
* Runtime configuration
* Environment variable overrides
* Typed pathlib.Path usage

#### Logging

Structured application logging with:

* Console output
* File logging
* Formatter abstraction
* Logger lifecycle management

#### State Management

In-memory task lifecycle tracking.

Supports:

* Create
* Retrieve
* Update
* Delete
* List

#### Artifact Management

In-memory artifact tracking.

Supports:

* Create
* Retrieve
* Update
* Delete
* List

#### Model Gateway

Model interaction abstraction layer.

Current implementation:

* StubModelAdapter

Future implementations:

* Qwen
* DeepSeek
* OpenAI-compatible APIs
* Local inference engines

#### Runtime Context

Centralized service container providing:

* Configuration
* Logging
* State Management
* Model Gateway

#### Orchestrator

Foundation orchestration shell for coordinating runtime services.

#### Runtime Bootstrap

Application startup and shutdown management.

#### Executor

Minimal execution framework that:

* Accepts task requests
* Tracks lifecycle state
* Routes requests through the model gateway
* Returns execution results

No planning or autonomous behavior is implemented yet.

---

## Repository Layout

```text
src/
└── qwen3_coder_next/
    ├── adapters/
    ├── artifacts/
    ├── bootstrap/
    ├── config/
    ├── contracts/
    ├── execution/
    ├── logging/
    ├── runtime/
    ├── state/
    ├── prompts/
    └── utils/

tests/
├── smoke/
├── unit/
└── integration/

configs/
docs/
scripts/
```

---
=======
Part 1 Foundation, Step 11 complete.

This repository currently contains a modular foundation layer with contracts, configuration, logging, state management, model gateway abstraction, runtime orchestration, artifact management, execution skeleton, and planning foundation. It does not include real AI functionality, memory, vector databases, tools, repository intelligence, evaluation, recovery logic, multi-agent workflows, or business logic.


## Requirements

* Python 3.13+
* uv

---

## Installation

```powershell
git clone <https://github.com/neural-agi/Qwen3-Coder-Next>
cd Qwen3-Coder-Next
uv sync
```

---

## Run

```powershell
uv run python -m qwen3_coder_next
```

Example output:

```text
2026-06-08 13:52:14 | INFO | qwen3_coder_next.bootstrap.runtime | Qwen3-Coder-Next Foundation Runtime Starting
2026-06-08 13:52:14 | INFO | qwen3_coder_next.bootstrap.runtime | Repository Skeleton Loaded
2026-06-08 13:52:14 | INFO | qwen3_coder_next.bootstrap.runtime | Shutdown Complete
```

---

## Testing

Run the complete test suite:

```powershell
uv run python -m unittest discover -s tests -v
```

Current result:

```text
24 tests passed
```

---

## Roadmap

### Foundation Phase

* [x] Repository Skeleton
* [x] Contracts
* [x] Configuration
* [x] Logging
* [x] State Management
* [x] Model Gateway
* [x] Runtime Context
* [x] Orchestrator
* [x] Artifact Management
* [x] Runtime Bootstrap
* [x] Execution Framework

### Future Development

* [ ] Prompt Management System
* [ ] Tool Registry
* [ ] Memory Layer
* [ ] Repository Intelligence
* [ ] Planning Engine
* [ ] Agent Workflow Runtime
* [ ] Code Generation Pipelines
* [ ] Multi-Model Support
* [ ] Autonomous Coding Workflows

---

## License

License to be determined.
=======
configs/
docs/
scripts/
```
## Project Documentation

Core project documentation is located in:

```text
documents/
```

Important files:

- vision.md
- architecture.md
- roadmap.md
- progress.md
- coding_standards.md
- session_handoff.md
