"""Tool-specific exceptions."""


class ToolError(Exception):
    """Base error for tool operations."""


class DuplicateToolError(ToolError):
    """Raised when registering a tool that already exists."""


class ToolNotFoundError(ToolError):
    """Raised when a requested tool does not exist."""
