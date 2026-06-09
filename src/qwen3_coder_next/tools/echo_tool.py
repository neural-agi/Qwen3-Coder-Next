"""Deterministic echo tool."""

from qwen3_coder_next.tools.contracts import ToolDefinition, ToolRequest, ToolResult, ToolStatus
from qwen3_coder_next.tools.tool import Tool


class EchoTool(Tool):
    """Return the input unchanged."""

    def __init__(self) -> None:
        self._definition = ToolDefinition(
            tool_id="echo-tool",
            name="echo",
            description="Return the input unchanged.",
        )

    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""

        return self._definition

    def execute(self, request: ToolRequest) -> ToolResult:
        """Return the request input without side effects."""

        return ToolResult(
            tool_name=self.definition.name,
            status=ToolStatus.SUCCEEDED,
            output=request.input,
        )
