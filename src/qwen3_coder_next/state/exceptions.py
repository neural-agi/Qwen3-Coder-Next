"""Custom exceptions for the in-memory state store."""


class StateNotFoundError(KeyError):
    """Raised when a requested task state does not exist."""


class DuplicateStateError(ValueError):
    """Raised when attempting to create a task state that already exists."""
