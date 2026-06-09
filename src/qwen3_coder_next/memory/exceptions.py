"""Memory-specific exceptions."""


class MemoryError(Exception):
    """Base error for memory operations."""


class DuplicateMemoryError(MemoryError):
    """Raised when creating a memory that already exists."""


class MemoryNotFoundError(MemoryError):
    """Raised when a requested memory does not exist."""
