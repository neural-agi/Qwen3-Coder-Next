"""Smoke tests for Part 5 Step 8 memory observability and audit events."""

import unittest
from datetime import UTC, datetime

from qwen3_coder_next.memory import (
    MemoryAuditRecorder,
    MemoryItem,
    MemoryLifecycleAction,
    MemoryLifecycleActionType,
    MemoryState,
    MemoryTier,
    deserialize_memory_state,
    serialize_memory_state,
)


class MemoryStep8Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = MemoryState(state_id="audit-state")
        self.memory = MemoryItem(
            memory_id="memory-1",
            tier=MemoryTier.PROJECT,
            subject="decision",
            content="preserve provenance",
            source="test",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            references=("ref-1",),
            schema_version=3,
        )
        self.recorder = MemoryAuditRecorder()

    def test_records_write_promotion_and_eviction_in_order(self) -> None:
        state = self.recorder.record_memory_write(self.state, self.memory)
        state = self.recorder.record_memory_read(state, self.memory)
        promoted = MemoryLifecycleAction(
            MemoryLifecycleActionType.PROMOTE, self.memory, MemoryTier.GLOBAL, "approved"
        )
        evicted = MemoryLifecycleAction(MemoryLifecycleActionType.EVICT, self.memory, reason="expired")
        state = self.recorder.record_lifecycle_action(state, promoted)
        state = self.recorder.record_lifecycle_action(state, evicted)
        self.assertEqual(
            tuple(event.event_type for event in state.memory_events),
            ("memory_write", "memory_read", "memory_promoted", "memory_evicted"),
        )
        self.assertEqual(state.memory_events[0].payload["memory"]["schema_version"], 3)
        self.assertEqual(state.memory_events[0].references, ("memory-1", "ref-1"))

    def test_event_serialization_is_deterministic_and_immutable(self) -> None:
        updated = self.recorder.record_memory_write(self.state, self.memory)
        serialized = serialize_memory_state(updated)
        self.assertEqual(serialized, serialize_memory_state(deserialize_memory_state(serialized)))
        self.assertEqual(self.state.memory_events, ())
        self.assertNotEqual(updated, self.state)

    def test_malformed_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.recorder.record_memory_write(self.state, object())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.recorder.record_event(self.state, object())  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.recorder.record_memory_write(self.state, self.memory, operation="")


if __name__ == "__main__":
    unittest.main()
