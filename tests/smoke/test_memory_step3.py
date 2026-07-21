"""Smoke tests for Part 5 Step 3 session memory storage."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.contracts import TaskRequest
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.memory import (
    MalformedMemorySerializedDataError,
    MemoryItem,
    MemoryState,
    MemoryTier,
    SessionMemoryStore,
    SessionSummary,
)
from qwen3_coder_next.runtime import Orchestrator


class MemoryStep3SmokeTest(unittest.TestCase):
    """Verify deterministic session-memory persistence."""

    def _build_settings(self, workspace_root: Path) -> AppSettings:
        return AppSettings(
            environment=EnvironmentName.TESTING,
            debug=True,
            workspace_root=workspace_root,
            artifacts_dir=workspace_root / "artifacts",
            data_dir=workspace_root / "data",
            logs_dir=workspace_root / "logs",
        )

    def test_deterministic_session_persistence(self) -> None:
        """Persist the same session state deterministically."""

        with TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "session.json"
            store = SessionMemoryStore(storage_path)
            summary = SessionSummary(
                session_id="session-001",
                goal="Keep session history durable.",
                outcomes=("initial summary",),
                decisions=("persist summaries",),
                open_questions=("how to aggregate later?",),
            )

            first = store.append_session_summary("session-001", summary)
            second = store.append_session_summary(
                "session-002",
                SessionSummary(
                    session_id="session-002",
                    goal="Keep session history durable.",
                    outcomes=("secondary summary",),
                    decisions=("persist summaries",),
                    open_questions=(),
                ),
            )
            serialized_once = store.serialize()
            serialized_twice = store.serialize()

            self.assertEqual(serialized_once, serialized_twice)
            self.assertEqual(first.state_id, "session-001")
            self.assertEqual(second.state_id, "session-002")
            self.assertTrue(storage_path.exists())

            reloaded = SessionMemoryStore(storage_path)
            self.assertEqual(reloaded.get_session_state("session-001"), first)
            self.assertEqual(reloaded.get_session_state("session-002"), second)

    def test_append_only_session_evolution(self) -> None:
        """Append session records without mutating the previous snapshot."""

        store = SessionMemoryStore()
        original = MemoryState(state_id="session-003")
        created = store.create_session_state(original)
        evolved = store.append_session_summary(
            "session-003",
            SessionSummary(
                session_id="session-003",
                goal="Track state evolution.",
                outcomes=("append-first",),
                decisions=("keep snapshots immutable",),
                open_questions=(),
            ),
        )

        self.assertEqual(created, original)
        self.assertEqual(created.session_summaries, ())
        self.assertEqual(evolved.session_summaries[0].goal, "Track state evolution.")
        self.assertEqual(evolved.state_id, "session-003")
        self.assertEqual(evolved.state_version, 2)
        self.assertEqual(evolved.revision_history[0].revision_id, "session-003-rev-0002")

    def test_serialization_round_trip(self) -> None:
        """Round-trip the store through canonical serialization."""

        store = SessionMemoryStore()
        store.append_memory_item(
            "session-004",
            MemoryItem(
                memory_id="memory-001",
                tier=MemoryTier.SESSION,
                subject="session memory",
                content="compatibility with MemoryState",
                source="session-store",
                confidence="high",
            ),
        )

        serialized = store.serialize()
        reloaded = SessionMemoryStore.deserialize(serialized)

        self.assertEqual(reloaded.serialize(), serialized)
        self.assertEqual(reloaded.get_session_state("session-004"), store.get_session_state("session-004"))

    def test_identifier_stability_and_version_preservation(self) -> None:
        """Preserve identifiers and version fields through persistence."""

        store = SessionMemoryStore()
        state = store.append_session_summary(
            "session-005",
            SessionSummary(
                session_id="session-005",
                goal="Preserve identifiers.",
                outcomes=("stable ids",),
                decisions=("version stays intact",),
                open_questions=(),
            ),
        )

        self.assertEqual(state.state_id, "session-005")
        self.assertEqual(state.state_version, 2)
        self.assertEqual(state.revision_history[0].revision_number, 2)
        self.assertEqual(state.revision_history[0].revision_id, "session-005-rev-0002")

        reloaded = SessionMemoryStore.deserialize(store.serialize())
        self.assertEqual(reloaded.get_session_state("session-005").state_version, 2)

    def test_malformed_payload_handling(self) -> None:
        """Reject malformed session-store payloads."""

        with self.assertRaises(MalformedMemorySerializedDataError):
            SessionMemoryStore.deserialize("{not-json")

        with self.assertRaises(MalformedMemorySerializedDataError):
            SessionMemoryStore.deserialize({"session_states": "not-a-collection"})

        with self.assertRaises(MalformedMemorySerializedDataError):
            SessionMemoryStore.deserialize({"session_states": ["not-a-mapping"]})

    def test_immutable_behavior_and_memorystate_compatibility(self) -> None:
        """Store and reload immutable MemoryState snapshots without mutation."""

        store = SessionMemoryStore()
        memory_state = MemoryState(
            state_id="session-006",
            memory_items=(
                MemoryItem(
                    memory_id="memory-002",
                    tier=MemoryTier.SESSION,
                    subject="compatibility",
                    content="store the state snapshot directly",
                    source="memory-state",
                    confidence="medium",
                ),
            ),
        )

        created = store.create_session_state(memory_state)
        self.assertEqual(memory_state.memory_items[0].memory_id, "memory-002")
        self.assertEqual(created, memory_state)

        evolved = store.append_session_summary(
            "session-006",
            SessionSummary(
                session_id="session-006",
                goal="Keep snapshots immutable.",
                outcomes=("append-only",),
                decisions=(),
                open_questions=(),
            ),
        )
        self.assertEqual(memory_state.session_summaries, ())
        self.assertEqual(evolved.session_summaries[0].goal, "Keep snapshots immutable.")

    def test_runtime_working_memory_compatibility(self) -> None:
        """Accept working-memory snapshots produced by the runtime."""

        with TemporaryDirectory() as temp_dir:
            try:
                orchestrator = Orchestrator.initialize(self._build_settings(Path(temp_dir)))
                orchestrator.activate_task(TaskRequest(task_id="task-session-007", objective="Session compatibility"))
                working_memory = orchestrator.working_memory

                store = SessionMemoryStore()
                store.create_session_state(working_memory)

                self.assertEqual(store.get_session_state(working_memory.state_id).state_id, working_memory.state_id)
                self.assertEqual(store.get_session_state(working_memory.state_id), working_memory)
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")


if __name__ == "__main__":
    unittest.main(verbosity=2)
