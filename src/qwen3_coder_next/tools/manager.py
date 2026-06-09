"""Stable API layer for tool management."""

from qwen3_coder_next.tools.registry import ToolRegistry
from qwen3_coder_next.tools.tool import Tool


class ToolManager:
    """Manage tool operations through a registry."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        """Initialize the tool manager with an in-memory registry."""

        self._registry = registry or ToolRegistry()

    def register_tool(self, tool: Tool) -> Tool:
        """Register a tool."""

        return self._registry.register(tool)

    def get_tool(self, name: str) -> Tool:
        """Retrieve a tool."""

        return self._registry.get(name)

    def list_tools(self) -> list[Tool]:
        """List all registered tools."""

        return self._registry.list()
