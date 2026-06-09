"""Smoke tests for the tool framework."""

import unittest

from qwen3_coder_next.tools import (
    EchoTool,
    ToolDefinition,
    ToolManager,
    ToolRegistry,
    ToolRequest,
    ToolResult,
    ToolStatus,
)
from qwen3_coder_next.tools.exceptions import DuplicateToolError, ToolNotFoundError


class ToolFrameworkSmokeTest(unittest.TestCase):
    """Verify tool contracts, registry, manager, and deterministic execution."""

    def test_tool_contracts_can_be_created(self) -> None:
        """Create each tool contract type."""

        definition = ToolDefinition(
            tool_id="tool-001",
            name="echo",
            description="Echo input",
        )
        request = ToolRequest(tool_name="echo", input="hello")
        result = ToolResult(tool_name="echo", status=ToolStatus.SUCCEEDED, output="hello")

        self.assertEqual(definition.name, "echo")
        self.assertEqual(request.input, "hello")
        self.assertEqual(result.output, "hello")

    def test_tool_registry_registration_retrieval_and_listing(self) -> None:
        """Register a tool, retrieve it, and list it."""

        registry = ToolRegistry()
        tool = EchoTool()

        registry.register(tool)

        self.assertIs(registry.get("echo"), tool)
        self.assertEqual(registry.list(), [tool])

    def test_tool_registry_duplicate_and_missing_handling(self) -> None:
        """Raise the expected exceptions for duplicate and missing tools."""

        registry = ToolRegistry()
        tool = EchoTool()

        registry.register(tool)

        with self.assertRaises(DuplicateToolError):
            registry.register(tool)

        with self.assertRaises(ToolNotFoundError):
            registry.get("missing")

    def test_echo_tool_executes_deterministically(self) -> None:
        """Return the input unchanged."""

        tool = EchoTool()
        result = tool.execute(ToolRequest(tool_name="echo", input="hello"))

        self.assertEqual(result, ToolResult(tool_name="echo", status=ToolStatus.SUCCEEDED, output="hello"))

    def test_tool_manager_wraps_registry_operations(self) -> None:
        """Use the manager to proxy registry operations."""

        manager = ToolManager()
        tool = EchoTool()

        manager.register_tool(tool)

        self.assertIs(manager.get_tool("echo"), tool)
        self.assertEqual(manager.list_tools(), [tool])
