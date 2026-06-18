"""Smoke tests for the local tooling filesystem operations layer."""

from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    DeterministicFileSystemOperator,
    FileSystemOperation,
    FileSystemOperationOutcome,
    FileSystemOperationType,
    FileSystemOperator,
)


class LocalToolingOperationsSmokeTest(TestCase):
    """Verify filesystem operation contracts and deterministic execution."""

    def test_operation_contracts_can_be_created(self) -> None:
        """Create operation and outcome contracts."""

        operation = FileSystemOperation(
            operation_id="op-001",
            operation_type=FileSystemOperationType.WRITE,
            path=Path("docs/example.txt"),
            content="hello",
        )
        outcome = FileSystemOperationOutcome(
            operation_id="op-001",
            operation_type=FileSystemOperationType.WRITE,
            path=Path("docs/example.txt"),
            success=True,
            exists=True,
            content="hello",
        )

        self.assertEqual(operation.content, "hello")
        self.assertTrue(outcome.success)

    def test_deterministic_operator_executes_read_write_and_exists(self) -> None:
        """Execute operations through the deterministic in-memory operator."""

        self.assertTrue(issubclass(DeterministicFileSystemOperator, FileSystemOperator))

        operator = DeterministicFileSystemOperator()
        path = Path("docs/example.txt")

        write_outcome = operator.execute(
            FileSystemOperation(
                operation_id="op-002",
                operation_type=FileSystemOperationType.WRITE,
                path=path,
                content="hello",
            )
        )
        self.assertTrue(write_outcome.success)
        self.assertTrue(write_outcome.exists)
        self.assertEqual(write_outcome.content, "hello")

        read_outcome = operator.execute(
            FileSystemOperation(
                operation_id="op-003",
                operation_type=FileSystemOperationType.READ,
                path=path,
            )
        )
        self.assertTrue(read_outcome.success)
        self.assertTrue(read_outcome.exists)
        self.assertEqual(read_outcome.content, "hello")

        exists_outcome = operator.execute(
            FileSystemOperation(
                operation_id="op-004",
                operation_type=FileSystemOperationType.EXISTS,
                path=path,
            )
        )
        self.assertTrue(exists_outcome.success)
        self.assertTrue(exists_outcome.exists)
