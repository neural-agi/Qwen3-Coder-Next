"""Smoke tests for core contract creation."""

from datetime import UTC, datetime
import unittest

from qwen3_coder_next.contracts import (
    ArtifactRecord,
    ArtifactType,
    MessageRecord,
    ModelRequest,
    ModelResponse,
    RuntimeConfig,
    TaskRequest,
    TaskResult,
    TaskState,
    TaskStatus,
)


class ContractCreationSmokeTest(unittest.TestCase):
    """Verifies that all core contracts can be instantiated."""

    def test_contract_creation(self) -> None:
        """Create one instance of each contract type."""
        now = datetime.now(UTC)

        task_request = TaskRequest(
            task_id="task-001",
            objective="Validate core contracts",
            metadata={"source": "smoke-test"},
        )
        task_result = TaskResult(
            task_id="task-001",
            success=True,
            summary="Contracts instantiated successfully.",
            outputs={"created": True},
        )
        runtime_config = RuntimeConfig(
            environment="test",
            debug=True,
            workspace_root="D:/PARANJAY/Projects/Qwen-3-Coder-Next",
        )
        message_record = MessageRecord(
            role="system",
            content="Smoke test message.",
            timestamp=now,
        )
        task_state = TaskState(
            task_id="task-001",
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        artifact_record = ArtifactRecord(
            artifact_id="artifact-001",
            artifact_type=ArtifactType.REPORT,
            path="artifacts/report.txt",
            created_at=now,
        )
        model_request = ModelRequest(
            prompt="Hello",
            system_prompt="System",
        )
        model_response = ModelResponse(
            content="Acknowledged",
            model_name="stub-model",
            success=True,
        )

        self.assertEqual(task_request.task_id, "task-001")
        self.assertTrue(task_result.success)
        self.assertEqual(runtime_config.environment, "test")
        self.assertEqual(message_record.role, "system")
        self.assertEqual(task_state.status, TaskStatus.PENDING)
        self.assertEqual(artifact_record.artifact_type, ArtifactType.REPORT)
        self.assertEqual(model_request.prompt, "Hello")
        self.assertTrue(model_response.success)


if __name__ == "__main__":
    print("Successful creation of all contract types.")
    unittest.main(verbosity=2)
