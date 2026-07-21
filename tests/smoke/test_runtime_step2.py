"""Smoke tests for Part 5 Step 2 runtime-owned working memory."""

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.contracts import TaskRequest
from qwen3_coder_next.execution import Executor
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.memory import MemoryItem, MemoryState, MemoryTier
from qwen3_coder_next.runtime import Orchestrator


class RuntimeStep2SmokeTest(unittest.TestCase):
    """Verify transient working memory is owned by runtime state."""

    def _build_settings(self, workspace_root: Path) -> AppSettings:
        return AppSettings(
            environment=EnvironmentName.TESTING,
            debug=True,
            workspace_root=workspace_root,
            artifacts_dir=workspace_root / "artifacts",
            data_dir=workspace_root / "data",
            logs_dir=workspace_root / "logs",
        )

    def test_working_memory_exists_in_runtime_state(self) -> None:
        """Expose a deterministic working-memory snapshot on runtime context."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))

                self.assertIsInstance(orchestrator.working_memory, MemoryState)
                self.assertEqual(orchestrator.active_task_id, None)
                self.assertEqual(orchestrator.working_memory.state_id, "runtime-working-memory")
                self.assertEqual(orchestrator.working_memory.memory_items, ())
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_working_memory_is_task_scoped_and_transient(self) -> None:
        """Reset transient working memory when the active task changes."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))
                first_request = TaskRequest(task_id="task-wm-1", objective="Capture runtime context")
                second_request = TaskRequest(task_id="task-wm-2", objective="Replace runtime context")

                orchestrator.activate_task(first_request)
                first_snapshot = orchestrator.working_memory
                orchestrator.append_working_memory_item(
                    MemoryItem(
                        memory_id="wm-001",
                        tier=MemoryTier.WORKING,
                        subject="task-one",
                        content="keep current task context",
                        source="runtime",
                        timestamp=datetime.fromtimestamp(0, UTC),
                        confidence="high",
                    )
                )

                self.assertEqual(orchestrator.active_task_id, "task-wm-1")
                self.assertEqual(orchestrator.working_memory.state_id, "task-wm-1-working-memory")
                self.assertEqual(orchestrator.working_memory.memory_items[0].memory_id, "wm-001")

                orchestrator.activate_task(second_request)

                self.assertEqual(first_snapshot.memory_items, ())
                self.assertEqual(orchestrator.active_task_id, "task-wm-2")
                self.assertEqual(orchestrator.working_memory.state_id, "task-wm-2-working-memory")
                self.assertEqual(orchestrator.working_memory.memory_items, ())
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_working_memory_can_be_reused_within_single_active_task(self) -> None:
        """Append multiple items against a single transient snapshot."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))
                orchestrator.activate_task(TaskRequest(task_id="task-wm-3", objective="Reuse memory"))

                first = MemoryItem(
                    memory_id="wm-002",
                    tier=MemoryTier.WORKING,
                    subject="first",
                    content="first context item",
                    source="runtime",
                    confidence="medium",
                )
                second = MemoryItem(
                    memory_id="wm-003",
                    tier=MemoryTier.WORKING,
                    subject="second",
                    content="second context item",
                    source="runtime",
                    confidence="medium",
                )

                first_snapshot = orchestrator.append_working_memory_item(first)
                second_snapshot = orchestrator.append_working_memory_item(second)

                self.assertEqual(first_snapshot.memory_items, (first,))
                self.assertEqual(second_snapshot.memory_items, (first, second))
                self.assertEqual(orchestrator.working_memory.memory_items, (first, second))
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_working_memory_state_is_immutable_and_deterministic(self) -> None:
        """Preserve snapshot immutability and deterministic append behavior."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))
                request = TaskRequest(task_id="task-wm-4", objective="Immutable memory")
                context = orchestrator.context.activate_task(request)
                memory_item = MemoryItem(
                    memory_id="wm-004",
                    tier=MemoryTier.WORKING,
                    subject="snapshot",
                    content="immutable snapshot",
                    source="runtime",
                    confidence="low",
                )

                evolved_once = context.append_working_memory_item(memory_item)
                evolved_twice = context.append_working_memory_item(memory_item)

                self.assertEqual(context.working_memory.memory_items, ())
                self.assertEqual(evolved_once.working_memory.memory_items, (memory_item,))
                self.assertEqual(evolved_once, evolved_twice)
                self.assertEqual(evolved_once.working_memory.state_version, 2)
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_malformed_payload_handling(self) -> None:
        """Reject malformed runtime working-memory updates."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))

                with self.assertRaises(ValueError):
                    orchestrator.context.with_working_memory_snapshot("not-a-memory-state")  # type: ignore[arg-type]

                with self.assertRaises(ValueError):
                    orchestrator.append_working_memory_item("not-a-memory-item")  # type: ignore[arg-type]
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_executor_reuses_runtime_working_memory_for_current_task(self) -> None:
        """Activate runtime working memory as part of the task lifecycle."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))
                executor = Executor(orchestrator)

                result = executor.execute(TaskRequest(task_id="task-wm-5", objective="Task lifecycle"))

                self.assertTrue(result.success)
                self.assertEqual(orchestrator.active_task_id, "task-wm-5")
                self.assertEqual(orchestrator.working_memory.state_id, "task-wm-5-working-memory")
                self.assertEqual(orchestrator.working_memory.memory_items, ())
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")


if __name__ == "__main__":
    unittest.main(verbosity=2)
