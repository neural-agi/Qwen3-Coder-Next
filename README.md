# Qwen3CoderNext

Qwen3CoderNext is a local first coding agent framework designed to provide Codex like project assistance while running primarily on user controlled infrastructure.

The project is being built incrementally from a clean, testable foundation toward a full coding agent platform capable of repository understanding, planning, memory management, tool execution, and autonomous development workflows.

---

## Current Status

### Part 1: Foundation Layer ✅

Completed:

* Repository Skeleton
* Core Contracts
* Configuration System
* Logging Infrastructure
* State Management
* Model Gateway
* Runtime Orchestration Shell
* Artifact Management
* Runtime Bootstrap
* Execution Framework
* Planning Foundation
* Prompt Infrastructure
* Memory Foundation
* Tool Framework
* Evaluation Foundation

### Part 2: Filesystem + Local Tooling 🚧

Completed:

* Step 1: Policy & Schema Boundaries
* Step 2: Workspace Resolution

Current Target:

* Step 3: Filesystem Operations Implementation

### Validation Status

```text
48 tests passing
0 failures
```

---

## Vision

Qwen3CoderNext aims to become a modular coding agent platform capable of:

* Repository understanding
* Planning and task decomposition
* Memory and context management
* Tool execution
* Artifact generation
* Autonomous coding workflows
* Local first operation
* Multiple model backends

The project prioritizes maintainability, testability, and architectural clarity before advanced agent behavior is introduced.

---

## Architecture Overview

### Foundation Systems

| Component             | Purpose                                               |
| --------------------- | ----------------------------------------------------- |
| Contracts             | Shared immutable system contracts                     |
| Configuration         | Typed application settings and environment management |
| Logging               | Structured console and file logging                   |
| State Management      | Filesystem backed task lifecycle persistence          |
| Artifact Management   | Filesystem backed artifact persistence                |
| Model Gateway         | Model abstraction and routing layer                   |
| Planning Foundation   | Deterministic planning abstractions                   |
| Prompt Infrastructure | Prompt templates, registry, and loading               |
| Memory Foundation     | Persistent memory storage layer                       |
| Tool Framework        | Tool contracts, registry, and execution abstractions  |
| Evaluation Foundation | Evaluation contracts and scoring abstractions         |
| Runtime Context       | Centralized service container                         |
| Orchestrator          | Runtime service coordination                          |
| Runtime Bootstrap     | Startup and shutdown lifecycle                        |
| Executor              | Task execution workflow                               |

### Local Tooling Foundations

#### Local Tooling Contracts

* RequestEnvelope
* ResponseEnvelope
* WorkspaceContext
* ExecutionPolicy
* FileResult
* CommandResult
* ArtifactDescriptor
* AuditEvent

#### Workspace Resolution

* WorkspaceResolutionRequest
* WorkspaceResolutionResult
* WorkspaceResolver
* StaticWorkspaceResolver

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
    ├── evaluation/
    ├── execution/
    ├── local_tooling/
    ├── logging/
    ├── memory/
    ├── planning/
    ├── prompts/
    ├── runtime/
    ├── state/
    ├── tools/
    └── utils/

tests/
├── smoke/
├── unit/
└── integration/

configs/
documents/
scripts/
```

---

## Requirements

* Python 3.13+
* uv

---

## Installation

```bash
git clone https://github.com/neuralagi/Qwen3CoderNext.git
cd Qwen3CoderNext
uv sync
```

---

## Running

```bash
uv run python -m qwen3_coder_next
```

---

## Testing

Run the full test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Current result:

```text
48 tests passing
0 failures
```

---

## Roadmap

### Part 1: Foundation Layer ✅

* [x] Repository Skeleton
* [x] Core Contracts
* [x] Configuration System
* [x] Logging Infrastructure
* [x] State Management
* [x] Model Gateway
* [x] Runtime Context
* [x] Orchestrator
* [x] Artifact Management
* [x] Runtime Bootstrap
* [x] Execution Framework
* [x] Planning Foundation
* [x] Prompt Infrastructure
* [x] Memory Foundation
* [x] Tool Framework
* [x] Evaluation Foundation

### Part 2: Filesystem + Local Tooling 🚧

* [x] Policy & Schema Boundaries
* [x] Workspace Resolution
* [ ] Filesystem Operations
* [ ] Command Execution
* [ ] Repository Intelligence Foundations

### Future Development

* [ ] Repository Intelligence
* [ ] Advanced Planning Engine
* [ ] Agent Workflow Runtime
* [ ] Code Generation Pipelines
* [ ] MultiModel Support
* [ ] Autonomous Coding Workflows
* [ ] MultiAgent Coordination

---

## License

License to be determined.
