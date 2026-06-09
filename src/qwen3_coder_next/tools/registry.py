"""In-memory tool registry."""

from collections.abc import Iterable

from qwen3_coder_next.tools.exceptions import DuplicateToolError, ToolNotFoundError
from qwen3_coder_next.tools.tool import Tool


class ToolRegistry:
    """Store and retrieve tools by name."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        """Register a tool and return it."""

        name = tool.definition.name
        if name in self._tools:
            raise DuplicateToolError(f"Tool already exists for name={name!r}.")
        self._tools[name] = tool
        return tool

    def get(self, name: str) -> Tool:
        """Retrieve a registered tool."""

        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool not found for name={name!r}.") from exc

    def list(self) -> list[Tool]:
        """Return all registered tools."""

        return list(self._tools.values())

    def extend(self, tools: Iterable[Tool]) -> None:
        """Register multiple tools."""

        for tool in tools:
            self.register(tool)
