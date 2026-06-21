# Qwen3CoderNext

Local-first coding agent framework built for developers who want Codex-style repository assistance without surrendering control of their codebase.

Qwen3CoderNext is an open architecture for building autonomous coding agents that can understand repositories, plan work, manage memory, execute tools, and perform development workflows while running primarily on user-controlled infrastructure.

The project is being developed incrementally from a clean, testable foundation toward a fully capable coding agent platform.

> **Status**
>
> Early Development
>
> Foundation Layer Complete
>
> Local Tooling Layer Complete
>
> Agent Core Development Starting

---

# Why Qwen3CoderNext?

Most coding agents today are tightly coupled to specific providers, opaque execution environments, or rapidly growing codebases that become difficult to maintain.

Qwen3CoderNext takes a different approach.

The project prioritizes:

* Local-first operation
* Clean architecture
* Deterministic behavior
* Strong testing discipline
* Modular components
* Provider independence
* Long-term maintainability

The goal is not to create another chatbot.

The goal is to create a reusable foundation for building serious coding agents.

---

# Long-Term Vision

Qwen3CoderNext is being designed to support:

* Repository understanding
* Planning and task decomposition
* Persistent memory
* Tool execution
* Artifact generation
* Autonomous coding workflows
* Multi-model support
* Multi-agent collaboration

Future releases aim to evolve the framework from a deterministic execution platform into a fully autonomous development system.

---

# Current Progress

## Part 1: Foundation Layer

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

## Part 2: Local Tooling Layer

Completed:

* Workspace Resolution
* Filesystem Service Abstraction
* Safe File Reads
* Filesystem Operations
* Safe Writes and Patches
* Diff Generation
* Command Execution
* Artifact Registry
* Audit Logging
* Tool Adapter Integration

---

# What Works Today

Current capabilities include:

### Workspace Management

* Workspace resolution
* Repository boundary enforcement
* Execution policy support

### Filesystem Operations

* Safe file reads
* Controlled file mutations
* Patch application
* Deterministic execution

### Command Execution

* Local command runner
* Structured command results
* Error handling and policy enforcement

### Artifact Management

* Artifact registry
* Provenance tracking
* Immutable manifests
* Checksum verification
* Supersede history

### Audit Infrastructure

* Append-only audit records
* Sequence-numbered event tracking
* Persistent local storage
* Deterministic replay support

---

# Architecture Principles

Qwen3CoderNext follows several guiding principles:

### Deterministic First

Core infrastructure should be predictable, testable, and reproducible.

### Local First

User data and repositories remain under user control whenever possible.

### Modular by Design

Components are isolated behind contracts and can evolve independently.

### Testability Matters

Every major subsystem is developed alongside automated validation.

### Foundation Before Intelligence

The project intentionally builds infrastructure before advanced agent behavior.

---

# Validation

Current test status:

```text
104 tests passed
0 failures
```

Run the full suite:

```bash
uv run python -m unittest discover -s tests -v
```

---

# Roadmap

## Completed

* Foundation Layer
* Local Tooling Layer

## In Progress

* Agent Core

## Planned

* Advanced Planning
* Memory Systems
* Tool Ecosystem
* Repository Intelligence
* Autonomous Development Workflows
* Multi-Agent Architecture

---

# Project Philosophy

Many agent projects begin with autonomous behavior and attempt to add reliability later.

Qwen3CoderNext takes the opposite path.

The framework is being built from deterministic, testable infrastructure upward, with each layer validated before introducing additional intelligence.

The objective is to create a coding agent platform that remains understandable, maintainable, and extensible as complexity grows.

---

# Contributing

Contribution guidelines will be published as the project matures.

For now, feedback, architectural discussion, and issue reports are welcome.

---

# License

License to be determined.
