# Qwen3CoderNext

Qwen3CoderNext is a local-first coding agent framework designed to provide Codex-like project assistance while running primarily on user-controlled infrastructure.

The project is being built incrementally from a clean, testable foundation toward a full coding agent platform capable of repository understanding, planning, memory management, tool execution, and autonomous development workflows.

> Active Development
>
> Qwen3CoderNext is currently in early development.
> Part 1 (Foundation Layer) is complete.
> Part 2 (Filesystem + Local Tooling) is complete.
> Development is preparing to transition into Part 3 (Agent Core).
> The project is not yet a fully functional coding agent.

---

## Current Status

### Part 1: Foundation Layer

Completed:

* Repository Skeleton
* Core Contracts
* Configuration System
* Logging Infrastructure
* State Management
* Model Gateway
* Runtime Context
* Orchestrator
* Artifact Management
* Runtime Bootstrap
* Execution Framework
* Planning Foundation
* Prompt Infrastructure
* Memory Foundation
* Tool Framework
* Evaluation Foundation

### Part 2: Filesystem + Local Tooling

Completed:

* Policy and Schema Boundaries
* Workspace Resolution
* Filesystem Service Abstraction
* Safe File Reads
* Filesystem Operations
* Safe Writes and Patches
* Diff Generation
* Command Runner
* Artifact Registry and Audit Logging
* Tool Adapter and Integration Tests

### Next Target

* Part 3 Step 1: Agent Core Planning

### Validation Status

```text
104 tests passed
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
* Local-first operation
* Multiple model backends

The project prioritizes maintainability, testability, and architectural clarity before advanced agent behavior is introduced.

---

## Architecture Overview

### Foundation Systems

| Component             | Purpose                                                    |
| --------------------- | ---------------------------------------------------------- |
| Contracts             | Shared immutable system contracts                          |
| Configuration         | Typed application settings and environment management      |
| Logging               | Structured console and file logging                        |
| State Management      | Filesystem-backed task lifecycle persistence               |
| Artifact Management   | Filesystem-backed artifact persistence                     |
| Model Gateway         | Model abstraction and routing layer                        |
| Planning Foundation   | Deterministic planning abstractions                        |
| Prompt Infrastructure | Prompt templates, registry, and loading                    |
| Memory Foundation     | Persistent memory storage layer                            |
| Tool Framework        | Tool contracts, registry, and execution abstractions       |
| Evaluation Foundation | Evaluation contracts and scoring abstractions              |
| Runtime Context       | Centralized service container                              |
| Orchestrator          | Runtime service coordination                               |
| Runtime Bootstrap     | Startup and shutdown lifecycle                             |
| Executor              | Task execution workflow                                    |
| Local Tooling Layer   | Filesystem, command, artifact, audit, and adapter services |

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
* ArtifactProvenance
* ArtifactManifest
* AuditRecord

#### Workspace Resolution

* WorkspaceResolutionRequest
* WorkspaceResolutionResult
* WorkspaceResolver
* StaticWorkspaceResolver

#### Filesystem Service Abstraction

Current implementation:

* FileSystemOperationRequest
* FileSystemOperationResult
* FileSystemService
* DeterministicFileSystemService

#### Safe File Reads

Current implementation:

* FileReadErrorCode
* FileReadRequest
* FileReadResult
* FileReadService
* DeterministicFileReadService

#### Filesystem Operations

Current implementation:

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

#### Diff Generation

Current implementation:

* DiffRequest
* DiffResult
* DiffService
* DeterministicDiffService

#### Command Runner

Current implementation:

* CommandRunErrorCode
* CommandRequest
* CommandRunResult
* CommandRunner
* DeterministicCommandRunner

#### Artifact Registry and Audit Logging

Current implementation:

Artifact Registry

* ArtifactRegistryErrorCode
* ArtifactRegistryRequest
* ArtifactRegistryResult
* ArtifactRegistry
* DeterministicArtifactRegistry

Audit Logging

* AuditLoggerErrorCode
* AuditLoggerRequest
* AuditLoggerResult
* AuditLogger
* DeterministicAuditLogger

Capabilities:

* Immutable artifact manifests
* Artifact provenance tracking
* Registry-computed checksums
* Manifest supersede/archive history
* Append-only audit records
* Sequence-numbered event ordering
* Persistent local storage
* Deterministic reload and replay support

#### Tool Adapter

Current implementation:

* ToolAdapter
* ToolAdapterOperation
* DeterministicToolAdapter

---

## Testing

Run the full test suite:

```bash
uv run python -m unittest discover -s tests -v
```

Current result:

```text
104 tests passed
0 failures
```

---

## Roadmap

### Part 1: Foundation Layer

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

### Part 2: Filesystem + Local Tooling

* [x] Policy and Schema Boundaries
* [x] Workspace Resolution
* [x] Filesystem Service Abstraction
* [x] Safe File Reads
* [x] Filesystem Operations
* [x] Safe Writes and Patches
* [x] Diff Generation
* [x] Command Runner
* [x] Artifact Registry and Audit Logging
* [x] Tool Adapter and Integration Tests

### Future Development

* [ ] Part 3: Agent Core
* [ ] Part 4: Memory Systems
* [ ] Part 5: Tool Ecosystem
* [ ] Part 6: Repository Intelligence
* [ ] Part 7: Autonomous Development
* [ ] Part 8: Multi-Agent Architecture

---

## License

License to be determined.
