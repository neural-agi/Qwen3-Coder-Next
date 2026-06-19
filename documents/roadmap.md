# Qwen3-Coder-Next Roadmap

## Overview

This roadmap defines the planned development sequence for Qwen3-Coder-Next.

The project is intentionally developed in small, verifiable stages.

Each step should:

* Leave the repository in a working state
* Include automated tests
* Preserve architectural consistency
* Build upon previously completed components

---

# Part 1: Foundation Layer

Goal:

Establish the core infrastructure required by all future systems.

## Step 1

Repository Skeleton

Status: Complete

Objectives:

* Package structure
* Bootstrap entry point
* Basic project layout

---

## Step 2

Core Contracts

Status: Complete

Objectives:

* Task contracts
* Model contracts
* State contracts
* Artifact contracts

---

## Step 3

Configuration System

Status: Complete

Objectives:

* AppSettings
* Environment handling
* Environment variable overrides
* Path configuration

---

## Step 4

Logging Infrastructure

Status: Complete

Objectives:

* Structured logging
* File logging
* Console logging
* Logger lifecycle management

---

## Step 5

State Management

Status: Complete

Objectives:

* State store
* State manager
* Lifecycle operations
* Error handling

---

## Step 6

Model Gateway

Status: Complete

Objectives:

* Adapter abstraction
* Gateway layer
* Stub model adapter
* Request validation

---

## Step 7

Orchestration Shell

Status: Complete

Objectives:

* Runtime context
* Service composition
* Orchestrator shell

---

## Step 8

Artifact Management

Status: Complete

Objectives:

* Artifact store
* Artifact manager
* Artifact lifecycle operations

---

## Step 9

Runtime Bootstrap

Status: Complete

Objectives:

* Runtime initialization
* Service composition
* Startup/shutdown lifecycle

---

## Step 10

Execution Skeleton

Status: Complete

Objectives:

* Execution result contracts
* Task lifecycle transitions
* Executor integration
* State updates

---

## Step 11

Planning Foundation

Status: Complete

Objectives:

* Planner interfaces
* Plan contracts
* Basic planning workflow
* Execution preparation

Expected Deliverables:

* Planning contracts
* Planner abstraction
* Initial planner implementation
* Smoke tests

---

## Step 12

Prompt Infrastructure

Status: Complete

Objectives:

* Prompt registry
* Prompt loading
* Prompt templates
* Prompt versioning foundation

---

## Step 13

Memory Foundation

Status: Complete

Objectives:

* Memory contracts
* Memory interfaces
* Short-term memory layer
* Retrieval abstractions

---

## Step 14

Tool Framework

Status: Complete

Objectives:

* Tool contracts
* Tool registry
* Tool execution interfaces
* Tool result handling

---

## Step 15

Evaluation Foundation

Status: Complete

Objectives:

* Evaluation contracts
* Evaluation interfaces
* Result scoring abstractions

---

# Part 2: Filesystem + Local Tooling

Goal:

Provide the foundational local tooling surface for filesystem-adjacent workflows.

## Step 1

Policy and Schema Boundaries

Status: Complete

Objectives:

* Request and response envelopes
* Workspace context contracts
* Execution policy contracts
* File, command, artifact, and audit schemas

---

## Step 2

Workspace Resolution

Status: Complete

Objectives:

* Workspace resolution request and result
* Workspace resolver abstraction
* Deterministic workspace resolution

---

## Step 3

Filesystem Service Abstraction

Status: Complete

Objectives:

* Filesystem service abstraction
* Deterministic filesystem service
* Request and result contracts

---

## Step 4

Filesystem Operations

Status: Complete

Objectives:

* Minimal filesystem operation boundary
* Deterministic operation contracts
* No real filesystem execution

---

## Step 5

Diff Generation

Status: Complete

Objectives:

* Diff request contract
* Diff result contract
* Diff service abstraction
* Deterministic diff generation

---

## Step 6

Command Runner

Status: Complete

Objectives:

* Allowlisted local command execution
* Explicit working-directory control
* Output capture

---

## Step 7

Artifact Registry and Audit Logging

Status: Pending

Objectives:

* Persist outputs and references
* Record event traces

---

## Step 8

Tool Adapter and Integration Tests

Status: Pending

Objectives:

* Expose internal services through a consistent tool interface
* Prove end-to-end flow

---

# Part 3: Agent Core

Goal:

Introduce autonomous reasoning capabilities.

Planned Features:

* Goal decomposition
* Multi-step planning
* Execution workflows
* Retry mechanisms
* Failure recovery

Status: Not Started

---

# Part 4: Memory Systems

Goal:

Enable persistent knowledge retention.

Planned Features:

* Working memory
* Episodic memory
* Retrieval systems
* Context management

Status: Not Started

---

# Part 5: Tool Ecosystem

Goal:

Allow interaction with external systems.

Planned Features:

* File tools
* Repository tools
* Search tools
* Development tools
* Execution tools

Status: Not Started

---

# Part 6: Repository Intelligence

Goal:

Enable deep understanding of software projects.

Planned Features:

* Repository analysis
* Dependency mapping
* Code navigation
* Change impact analysis

Status: Not Started

---

# Part 7: Autonomous Development

Goal:

Perform increasingly complex software engineering tasks.

Planned Features:

* Feature implementation
* Bug fixing
* Refactoring
* Test generation
* Documentation generation

Status: Not Started

---

# Part 8: Multi-Agent Architecture

Goal:

Support coordinated agent workflows.

Planned Features:

* Specialized agents
* Task delegation
* Agent communication
* Shared memory

Status: Not Started

---

# Long-Term Vision

Qwen3-Coder-Next should evolve into a highly capable software engineering platform capable of:

* Understanding large repositories
* Planning complex engineering tasks
* Executing development workflows
* Managing generated artifacts
* Evaluating results
* Recovering from failures
* Coordinating multiple specialized agents

The system should remain modular, testable, and maintainable throughout its evolution.
