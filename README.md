# Qwen3-Coder-Next

Qwen3-Coder-Next is a local-first coding agent framework designed to provide Codex-like project assistance while running primarily on user-controlled infrastructure.

The project is currently in the Foundation Phase, where the focus is on building a clean, modular, and testable architecture before introducing planning systems, memory, repository intelligence, tool execution, and autonomous coding workflows.

## Current Status

### Part 1: Foundation

Completed:

* Step 1: Repository Skeleton
* Step 2: Core Contracts
* Step 3: Configuration System
* Step 4: Logging Infrastructure
* Step 5: In-Memory State Management
* Step 6: Model Gateway Abstraction
* Step 7: Runtime Orchestration Shell
* Step 8: Artifact Management
* Step 9: Runtime Bootstrap Layer
* Step 10: Execution Framework
* Step 11: Planning Foundation
* Step 12: Prompt Infrastructure
* Step 13: Memory Foundation
* Step 14: Tool Framework
* Step 15: Evaluation Foundation

Current test status:

```text
40 tests passed
```

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
* PlanRequest
* PlanResult
* PromptTemplate

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

#### Planning Foundation

Minimal prompt-free planning layer for deterministic preparation work.

Current implementation:

* PlanRequest
* PlanResult
* PlanStep
* SimplePlanner

#### Prompt Infrastructure

Versioned prompt templates with in-memory registry and filesystem loading.

Current implementation:

* PromptTemplate
* PromptRegistry
* PromptLoader

#### Memory Foundation

Foundational in-memory memory layer with immutable contracts and basic lifecycle operations.

Current implementation:

* MemoryEntry
* MemoryStore
* MemoryManager

#### Tool Framework

Foundational in-memory tool layer with immutable contracts, registry, manager, and deterministic example execution.

Current implementation:

* ToolDefinition
* ToolRequest
* ToolResult
* ToolRegistry
* ToolManager
* EchoTool

#### Evaluation Foundation

Foundational evaluation layer with immutable contracts, abstraction, and deterministic example evaluation.

Current implementation:

* EvaluationStatus
* EvaluationScore
* EvaluationRequest
* EvaluationOutcome
* EvaluationResult
* Evaluator
* SimpleEvaluator

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
    ├── planning/
    ├── prompts/
    ├── runtime/
    ├── state/
    └── utils/

tests/
├── smoke/
├── unit/
└── integration/

configs/
docs/
scripts/
```

## Requirements

* Python 3.13+
* uv

## Installation

```powershell
git clone <https://github.com/neural-agi/Qwen3-Coder-Next>
cd Qwen3-Coder-Next
uv sync
```

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

## Testing

Run the complete test suite:

```powershell
uv run python -m unittest discover -s tests -v
```

Current result:

```text
29 tests passed
```

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
* [x] Planning Foundation
* [x] Prompt Infrastructure

### Future Development

* [ ] Tool Registry
* [x] Memory Layer
* [x] Tool Framework
* [x] Evaluation Foundation
* [ ] Repository Intelligence
* [ ] Planning Engine
* [ ] Agent Workflow Runtime
* [ ] Code Generation Pipelines
* [ ] Multi-Model Support
* [ ] Autonomous Coding Workflows

## License

License to be determined.
