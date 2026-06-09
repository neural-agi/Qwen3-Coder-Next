"""Tool abstraction."""

from abc import ABC, abstractmethod

from qwen3_coder_next.tools.contracts import ToolDefinition, ToolRequest, ToolResult


class Tool(ABC):
    """Abstract tool interface."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""

    @abstractmethod
    def execute(self, request: ToolRequest) -> ToolResult:
        """Execute the tool for the supplied request."""
