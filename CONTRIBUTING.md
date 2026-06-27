# Contributing to Qwen3CoderNext

First off, thank you for your interest in contributing.

Qwen3CoderNext is being built incrementally with a strong emphasis on deterministic behavior, modular architecture, and long-term maintainability. Every contribution should preserve those principles.

---

# Before You Start

Before making significant changes:

* Check the project roadmap to understand the current development phase.
* Read the relevant architecture documentation in the `documents/` directory.
* For larger features or architectural changes, please open an issue first so the design can be discussed before implementation.

---

# Development Setup

Clone the repository:

```bash
git clone https://github.com/neural-agi/Qwen3-Coder-Next.git
cd Qwen3-Coder-Next
```

Install dependencies:

```bash
uv sync
```

---

# Running Tests

Before submitting a pull request, ensure the full test suite passes.

```bash
uv run python -m unittest discover -s tests -v
```

All existing tests should continue to pass. New functionality should include appropriate test coverage.

---

# Coding Guidelines

Please follow the project's existing architecture and coding style.

In particular:

* Keep components modular and focused on a single responsibility.
* Prefer extending existing contracts over introducing new ones.
* Avoid unnecessary abstraction or premature optimization.
* Preserve deterministic behavior wherever applicable.
* Maintain backward compatibility unless an intentional architectural change is being made.
* Keep documentation synchronized with implementation changes.

---

# Pull Requests

When opening a pull request:

* Clearly describe the problem being solved.
* Keep changes focused on a single logical feature or fix.
* Include tests for new functionality.
* Update documentation if behavior or architecture changes.

Large architectural refactors should be discussed before implementation.

---

# Reporting Issues

Bug reports should include:

* Expected behavior
* Actual behavior
* Steps to reproduce
* Relevant logs or error messages
* Environment information (Python version, operating system, etc.)

Feature requests are welcome. Please explain the motivation and how the proposal fits within the project's overall architecture.

---

# Project Philosophy

Qwen3CoderNext is being built **foundation first**.

The goal is not to ship the fastest possible coding agent, but to build one that is understandable, deterministic, testable, and maintainable.

Every subsystem should make the project easier to extend—not harder.

Thank you for helping improve the project.
