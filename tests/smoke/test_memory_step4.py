
"""Smoke tests for Part 5 Step 4 project memory persistence."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.memory import (
    MalformedMemorySerializedDataError,
    MemoryState,
    ProjectDecision,
    ProjectMemoryStore,
)


class MemoryStep4SmokeTest(unittest.TestCase):
    """Verify deterministic project-memory persistence."""

    def test_deterministic_project_persistence(self) -> None:
        """Persist the same project state deterministically."""

        with TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir) / "project.json"
            store = ProjectMemoryStore(storage_path)
            metadata = {"owner": "platform", "priority": 1}
            state = MemoryState(state_id="project-001")

            created = store.create_project_state(state, metadata=metadata)
            evolved = store.append_project_decision(
                "project-001",
                ProjectDecision(
                    project_id="project-001",
                    decision="Use explicit memory contracts.",
                    rationale="Stable persistence keeps project decisions durable.",
                    alternatives=("ad hoc notes",),
                    version=3,
                ),
            )

            serialized_once = store.serialize()
            serialized_twice = store.serialize()

            self.assertEqual(serialized_once, serialized_twice)
            self.assertEqual(created, state)
            self.assertEqual(evolved.project_decisions[0].version, 3)
            self.assertTrue(storage_path.exists())

            reloaded = ProjectMemoryStore(storage_path)
            self.assertEqual(reloaded.get_project_state("project-001"), evolved)
            self.assertEqual(reloaded.get_project_metadata("project-001"), metadata)
            self.assertEqual(reloaded.serialize(), serialized_once)

    def test_append_first_evolution_and_version_preservation(self) -> None:
        """Append project records without mutating the original snapshot."""

        store = ProjectMemoryStore()
        original = MemoryState(state_id="project-002")
        created = store.create_project_state(original)
        evolved = store.append_project_decision(
            "project-002",
            ProjectDecision(
                project_id="project-002",
                decision="Keep project memory append-only.",
                rationale="Preserves revision history across reloads.",
                alternatives=("overwrite state",),
                version=2,
            ),
        )

        self.assertEqual(created, original)
        self.assertEqual(original.project_decisions, ())
        self.assertEqual(evolved.project_decisions[0].version, 2)
        self.assertEqual(evolved.state_version, 2)
        self.assertEqual(evolved.revision_history[0].revision_id, "project-002-rev-0002")

    def test_serialization_round_trip(self) -> None:
        """Round-trip the store through canonical serialization."""

        store = ProjectMemoryStore()
        store.append_project_decision(
            "project-003",
            ProjectDecision(
                project_id="project-003",
                decision="Prefer deterministic project persistence.",
                rationale="Keeps reload behavior stable.",
                alternatives=(),
                version=5,
            ),
            metadata={"source": "smoke-test"},
        )

        serialized = store.serialize()
        reloaded = ProjectMemoryStore.deserialize(serialized)

        self.assertEqual(reloaded.serialize(), serialized)
        self.assertEqual(reloaded.get_project_state("project-003"), store.get_project_state("project-003"))
        self.assertEqual(reloaded.get_project_metadata("project-003"), {"source": "smoke-test"})

    def test_malformed_payload_handling(self) -> None:
        """Reject malformed project-store payloads."""

        with self.assertRaises(MalformedMemorySerializedDataError):
            ProjectMemoryStore.deserialize("{not-json")

        with self.assertRaises(MalformedMemorySerializedDataError):
            ProjectMemoryStore.deserialize({"project_records": "not-a-collection"})

        with self.assertRaises(MalformedMemorySerializedDataError):
            ProjectMemoryStore.deserialize(
                {
                    "project_records": [
                        {
                            "project_id": "project-004",
                            "state": "not-a-mapping",
                        }
                    ]
                }
            )

        with self.assertRaises(MalformedMemorySerializedDataError):
            ProjectMemoryStore.deserialize(
                {
                    "project_records": [
                        {
                            "project_id": "project-004",
                            "state": {"state_id": "project-999"},
                        }
                    ]
                }
            )

    def test_compatibility_with_memorystate(self) -> None:
        """Accept immutable MemoryState snapshots directly."""

        store = ProjectMemoryStore()
        memory_state = MemoryState(
            state_id="project-005",
            project_decisions=(
                ProjectDecision(
                    project_id="project-005",
                    decision="Persist project decisions.",
                    rationale="Required for durable project knowledge.",
                    alternatives=("temporary notes",),
                    version=4,
                ),
            ),
        )

        created = store.create_project_state(memory_state, metadata={"compatibility": True})

        self.assertEqual(created, memory_state)
        self.assertEqual(store.get_project_state("project-005"), memory_state)
        self.assertEqual(store.get_project_metadata("project-005"), {"compatibility": True})


if __name__ == "__main__":
    unittest.main(verbosity=2)
