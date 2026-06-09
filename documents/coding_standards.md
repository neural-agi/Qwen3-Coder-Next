# Qwen3-Coder-Next Coding Standards

## Purpose

This document defines the engineering standards for Qwen3-Coder-Next.

All future development should follow these guidelines unless a roadmap milestone explicitly requires a different approach.

The goal is consistency, maintainability, and long-term architectural stability.

---

# General Principles

## Simplicity First

Prefer simple solutions over complex solutions.

Avoid introducing additional abstractions unless they provide clear value.

Every component should be understandable by a developer reading it for the first time.

---

## Incremental Development

Development should occur in small, verifiable steps.

Each completed step must:

* Compile successfully
* Pass tests
* Leave the repository in a working state

Large rewrites should be avoided whenever possible.

---

## Foundation Stability

Completed foundation systems should remain stable.

Avoid modifying public interfaces unless:

* Required by the roadmap
* Required to fix a defect
* Required to improve architectural consistency

Breaking changes should be minimized.

---

# Project Structure

New modules should follow the existing package structure.

Example:

```text
feature/
├── __init__.py
├── exceptions.py
├── store.py
├── manager.py
└── tests
```

Not every package requires all files.

Only add files that provide clear value.

---

# Type Safety

## Required

All new code should use type hints.

Example:

```python
def get_state(task_id: str) -> TaskState:
    ...
```

Avoid untyped public interfaces.

---

## Preferred Types

Use:

* dataclass
* Enum
* StrEnum
* Path
* Typed collections

Avoid introducing alternative object systems without justification.

---

# Data Models

## Dataclasses

Use dataclasses for contracts and immutable data structures.

Preferred:

```python
@dataclass(frozen=True, slots=True)
class Example:
    value: str
```

Use immutable objects whenever practical.

---

## Contracts

Shared data structures belong in:

```text
contracts/
```

Do not duplicate contract definitions across modules.

---

# Logging

All operational systems should use the centralized logging infrastructure.

Preferred:

```python
logger = get_logger("qwen3_coder_next.example")
```

Avoid:

```python
print(...)
```

except for temporary debugging during development.

---

# Error Handling

Use explicit exception types.

Preferred:

```python
class ExampleError(Exception):
    pass
```

Avoid:

```python
raise Exception(...)
```

Use domain-specific exceptions whenever possible.

---

# State Management

State transitions should be explicit.

Preferred:

```text
PENDING
RUNNING
SUCCEEDED
FAILED
```

Avoid hidden or implicit state changes.

State mutations should remain observable and testable.

---

# Testing

## Required

All new features should include tests.

Minimum expectation:

* Smoke tests

Future phases may introduce:

* Unit tests
* Integration tests
* End-to-end tests

---

## Test Design

Tests should verify behavior rather than implementation details.

Preferred:

```python
assert result.success is True
```

Avoid:

```python
assert internal_variable == ...
```

unless the internal behavior is the feature being tested.

---

# Dependency Management

New dependencies should be introduced cautiously.

Before adding a dependency:

1. Determine whether the standard library can solve the problem.
2. Determine whether an existing dependency already solves it.
3. Determine whether the dependency aligns with project goals.

Prefer fewer dependencies.

---

# Architecture Rules

## Dependency Direction

Higher-level systems may depend on lower-level systems.

Lower-level systems should not depend on higher-level systems.

Example:

```text
Executor
    ↓
State Manager
```

Allowed.

```text
State Manager
    ↓
Executor
```

Not allowed.

---

## Separation of Concerns

Each module should have a clearly defined responsibility.

Examples:

Configuration:

* Settings
* Environment handling

Logging:

* Logging only

State:

* State only

Avoid mixing responsibilities.

---

# Documentation Requirements

When a roadmap step is completed:

Update:

* README.md
* docs/progress.md

If architecture changes:

Update:

* docs/architecture.md

If project direction changes:

Update:

* docs/roadmap.md
* docs/vision.md

Documentation should remain synchronized with implementation.

---

# Future Codex Instructions

Before making architectural decisions:

Read:

1. README.md
2. docs/vision.md
3. docs/architecture.md
4. docs/roadmap.md
5. docs/progress.md
6. docs/coding_standards.md

Follow established project patterns whenever possible.

Do not introduce new architectural styles unless a roadmap milestone requires them.

Maintain consistency with existing code.

Preserve readability and testability.

When uncertain, choose the simpler solution.
