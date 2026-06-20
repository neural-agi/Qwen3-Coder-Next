# Qwen3-Coder-Next Architecture

## Overview

Qwen3-Coder-Next follows a layered architecture designed to separate responsibilities and allow individual components to evolve independently.

Each layer exposes stable interfaces while minimizing coupling with other parts of the system.

The architecture emphasizes:

* Modularity
* Testability
* Extensibility
* Maintainability

---

## High-Level Architecture

```text
User Input
    │
    ▼
Runtime Bootstrap
    │
    ▼
Orchestrator
    │
    ▼
Executor
    │
    ├── State Manager
    ├── Artifact Manager
    ├── Model Gateway
    └── Future Systems
            ├── Planner
            ├── Memory
            ├── Tools
            ├── Evaluators
            └── Multi-Agent Coordination
```

---

## Foundation Layer

The foundation layer provides the core infrastructure required by all future systems.

### Contracts

Location:

```text
src/qwen3_coder_next/contracts
```

Purpose:

Defines immutable data structures shared across the application.

Examples:

* TaskRequest
* TaskState
* ModelRequest
* ModelResponse
* ArtifactRecord

Responsibilities:

* Shared type definitions
* Stable interfaces
* Cross-module communication

---

### Configuration

Location:

```text
src/qwen3_coder_next/config
```

Purpose:

Centralized application configuration.

Responsibilities:

* Environment handling
* Runtime settings
* Path configuration
* Environment variable overrides

Primary Objects:

* AppSettings
* EnvironmentName

---

### Logging

Location:

```text
src/qwen3_coder_next/logging
```

Purpose:

Centralized logging infrastructure.

Responsibilities:

* Structured logging
* File logging
* Console logging
* Logger lifecycle management

Primary Components:

* ApplicationLogger
* Formatter
* Logging Setup Utilities

---

### State Management

Location:

```text
src/qwen3_coder_next/state
```

Purpose:

Track task execution state.

Responsibilities:

* State creation
* State updates
* State retrieval
* State deletion

Current Implementation:

* Filesystem-backed store
* JSON persistence

Future Possibilities:

* Database-backed persistence
* Distributed state systems

---

### Artifact Management

Location:

```text
src/qwen3_coder_next/artifacts
```

Purpose:

Track generated outputs.

Responsibilities:

* Artifact registration
* Artifact retrieval
* Artifact updates
* Artifact deletion

Current Implementation:

* Filesystem-backed store
* JSON persistence

Future Possibilities:

* Filesystem storage
* Cloud storage
* Versioned artifacts

---

### Model Gateway

Location:

```text
src/qwen3_coder_next/adapters
```

Purpose:

Abstract model interaction behind a stable interface.

Responsibilities:

* Model request validation
* Adapter routing
* Provider abstraction

Current Implementation:

* StubModelAdapter

Future Possibilities:

* Qwen
* OpenAI
* Anthropic
* Local models
* Multi-model routing

---

## Runtime Layer

### Runtime Context

Location:

```text
src/qwen3_coder_next/runtime/context.py
```

Purpose:

Central container for runtime services.

Contains:

* Settings
* State Manager
* Artifact Manager
* Memory Manager
* Model Gateway
* Logger

---

### Orchestrator

Location:

```text
src/qwen3_coder_next/runtime/orchestrator.py
```

Purpose:

Top-level coordination layer.

Current Responsibilities:

* Service composition
* Runtime coordination
* Execution shell behavior

Future Responsibilities:

* Planning
* Task routing
* Workflow orchestration
* Agent coordination

---

### Planning Foundation

Location:

```text
src/qwen3_coder_next/planning
```

Purpose:

Provide the initial planning contracts and a deterministic planner abstraction for preparation work.

Current Implementation:

* PlanRequest
* PlanResult
* PlanStep
* PlanStatus
* Planner abstraction
* SimplePlanner

---

### Prompt Infrastructure

Location:

```text
src/qwen3_coder_next/prompts
```

Purpose:

Provide versioned prompt templates, a prompt registry, and deterministic filesystem loading.

Current Implementation:

* PromptFormat
* PromptTemplate
* PromptLoadRequest
* PromptLoadResult
* PromptRegistry
* PromptLoader

---

### Memory Foundation

Location:

```text
src/qwen3_coder_next/memory
```

Purpose:

Provide immutable memory contracts and a deterministic filesystem-backed store for basic lifecycle operations.

Current Implementation:

* MemoryKind
* MemoryEntry
* MemoryStore
* MemoryManager
* Filesystem-backed store
* JSON persistence

---

### Tool Framework

Location:

```text
src/qwen3_coder_next/tools
```

Purpose:

Provide immutable tool contracts, a registry, a manager, and a deterministic example tool.

Current Implementation:

* ToolStatus
* ToolDefinition
* ToolRequest
* ToolResult
* Tool abstraction
* ToolRegistry
* ToolManager
* EchoTool

---

### Evaluation Foundation

Location:

```text
src/qwen3_coder_next/evaluation
```

Purpose:

Provide immutable evaluation contracts, an evaluator abstraction, and a deterministic example evaluator.

Current Implementation:

* EvaluationStatus
* EvaluationScore
* EvaluationRequest
* EvaluationOutcome
* EvaluationResult
* Evaluator
* SimpleEvaluator

---

### Local Tooling Contracts

Location:

```text
src/qwen3_coder_next/local_tooling
```

Purpose:

Define the policy and schema boundaries for the filesystem-adjacent local tooling layer.

Current Implementation:

* RequestEnvelope
* ResponseEnvelope
* WorkspaceContext
* ExecutionPolicy
* FileResult
* CommandResult
* ArtifactDescriptor
* AuditEvent

### Local Tooling Resolution

Location:

```text
src/qwen3_coder_next/local_tooling
```

Purpose:

Provide a deterministic workspace resolution boundary without filesystem discovery.

Current Implementation:

* WorkspaceResolutionRequest
* WorkspaceResolutionResult
* WorkspaceResolver
* StaticWorkspaceResolver

Responsibilities:

* Workspace resolution contracts
* Deterministic workspace selection
* Stable request/result boundary

Current Limitations:

* No workspace discovery
* No path normalization
* No filesystem traversal
* No command execution
* No audit routing

### Filesystem Service Abstraction

Location:

```text
src/qwen3_coder_next/local_tooling
```

Purpose:

Provide a deterministic filesystem service boundary without introducing real filesystem operations.

Current Implementation:

* FileSystemOperationRequest
* FileSystemOperationResult
* FileSystemService
* DeterministicFileSystemService

Responsibilities:

* Filesystem service contracts
* Deterministic read/write/existence behavior
* Stable request/result boundary

Current Limitations:

* No real filesystem access
* No workspace discovery
* No path normalization
* No command execution
* No routing or adapters

### Safe File Reads

Location:

```text
src/qwen3_coder_next/local_tooling
```

Purpose:

Provide deterministic read-only file access with structured errors, previews, and digests.

Current Implementation:

* FileReadErrorCode
* FileReadRequest
* FileReadResult
* FileReadService
* DeterministicFileReadService

Responsibilities:

* Read-only file access semantics
* Preview generation
* Digest generation
* Structured error handling

Current Limitations:

* No write operations
* No patch operations
* No command execution
* No artifact registry
* No audit logging
* No tool adapter

### Filesystem Operations

Location:

```text
src/qwen3_coder_next/local_tooling
```

Purpose:

Provide deterministic filesystem operations and safe mutation support built on top of the filesystem service abstraction.

Current Implementation:

* FileSystemOperationType
* FileSystemOperation
* FileSystemOperationOutcome
* FileSystemOperator
* DeterministicFileSystemOperator
* FileMutationType
* FileMutationRequest
* FileMutationPreflightResult
* FileMutationResult
* FileMutationService
* DeterministicFileMutationService

Responsibilities:

* Filesystem operation contracts
* Deterministic read/write/existence execution
* Atomic write, append, and patch support
* Preflight validation for safe mutations
* Stable request/result boundary

Current Limitations:

* No real filesystem access
* No workspace discovery
* No path normalization
* No command execution
* No artifact registry
* No audit logging
* No routing or adapters

### Diff Generation

Location:

```text
src/qwen3_coder_next/local_tooling
```

Purpose:

Expose file diffs as first-class deterministic outputs for review and evaluation stages.

Current Implementation:

* DiffRequest
* DiffResult
* DiffService
* DeterministicDiffService

Responsibilities:

* Diff request and result contracts
* Deterministic diff generation
* Stable review-facing change representation

Current Limitations:

* No command execution
* No artifact registry
* No audit logging
* No tool adapter

### Command Runner

Location:

```text
src/qwen3_coder_next/local_tooling
```

Purpose:

Provide deterministic local command execution with allowlist control and explicit working-directory handling.

Current Implementation:

* CommandRunErrorCode
* CommandRequest
* CommandRunResult
* CommandRunner
* DeterministicCommandRunner

Responsibilities:

* Command request and result contracts
* Allowlisted command execution
* Workspace-relative working-directory control
* Output capture

Current Limitations:

* No shell execution
* No network access
* No tool adapter

---

### Tool Adapter

Location:

```text
src/qwen3_coder_next/local_tooling
```

Purpose:

Normalize local tooling requests and responses while routing to the deterministic local services.

Current Implementation:

* ToolAdapter
* ToolAdapterOperation
* DeterministicToolAdapter

Responsibilities:

* Request normalization
* Response normalization
* Workspace resolution
* Service routing
* Artifact capture
* Audit logging

Current Limitations:

* No autonomous behavior
* No repository intelligence
* No MCP integration
* No agent workflows

---

### Runtime Bootstrap

Location:

```text
src/qwen3_coder_next/bootstrap
```

Purpose:

Initialize the application runtime.

Responsibilities:

* Load configuration
* Initialize logging
* Build runtime context
* Create orchestrator
* Manage startup and shutdown

---

## Execution Layer

### Executor

Location:

```text
src/qwen3_coder_next/execution
```

Purpose:

Manage task execution lifecycle.

Current Lifecycle:

```text
PENDING
    │
    ▼
RUNNING
    │
    ▼
SUCCEEDED
```

Responsibilities:

* Task normalization
* State transitions
* Model invocation
* Execution result generation

Current Limitations:

* No artifact generation

---

## Future Layers

The following systems are planned but not yet implemented.

### Planning System

Responsibilities:

* Goal decomposition
* Task planning
* Execution strategy generation

---

### Memory System

Responsibilities:

* Long-term memory
* Short-term memory
* Retrieval mechanisms

---

### Tool System

Responsibilities:

* External tool execution
* Tool registration
* Tool routing

---

### Repository Intelligence

Responsibilities:

* Codebase understanding
* Dependency analysis
* Project reasoning

---

### Evaluation System

Responsibilities:

* Output validation
* Quality assessment
* Self-correction

---

### Multi-Agent Layer

Responsibilities:

* Agent coordination
* Specialized workers
* Task delegation

---

## Design Philosophy

The architecture intentionally starts simple.

Every layer should remain:

* Understandable
* Testable
* Replaceable

Complexity should be added only when required and only after the supporting infrastructure is stable.

The goal is to create a system that can evolve into a highly capable autonomous software engineering platform without sacrificing maintainability or architectural clarity.
