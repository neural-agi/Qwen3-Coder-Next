"""Smoke tests for Part 5 Step 7 global memory gating."""

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from qwen3_coder_next.memory import (
    GlobalMemoryStore,
    MemoryItem,
    MemoryLifecycleAction,
    MemoryLifecycleActionType,
    MemoryLifecyclePlan,
    MemoryTier,
)


class MemoryStep7Tests(unittest.TestCase):
    def _plan(self, target: MemoryTier) -> MemoryLifecyclePlan:
        item = MemoryItem(
            memory_id="project-memory",
            tier=MemoryTier.PROJECT,
            subject="decision",
            content="reusable rule",
            source="project",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            references=("source-1",),
            schema_version=4,
        )
        return MemoryLifecyclePlan(
            state_id="project-1",
            as_of=datetime(2026, 1, 2, tzinfo=UTC),
            actions=(MemoryLifecycleAction(MemoryLifecycleActionType.PROMOTE, item, target, "approved"),),
        )

    def test_global_promotion_requires_project_to_global_plan(self) -> None:
        store = GlobalMemoryStore()
        state = store.promote_from_plan(self._plan(MemoryTier.GLOBAL))
        promoted = state.memory_items[0]
        self.assertEqual(promoted.tier, MemoryTier.GLOBAL)
        self.assertEqual(promoted.references, ("source-1",))
        self.assertEqual(promoted.schema_version, 4)

    def test_gate_rejects_non_global_or_non_promotion_actions(self) -> None:
        store = GlobalMemoryStore()
        with self.assertRaises(ValueError):
            store.promote_from_plan(self._plan(MemoryTier.PROJECT))

    def test_global_store_round_trips_deterministically(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "global.json"
            first = GlobalMemoryStore(path)
            first.promote_from_plan(self._plan(MemoryTier.GLOBAL))
            serialized = first.serialize()
            second = GlobalMemoryStore.deserialize(serialized)
            self.assertEqual(serialized, second.serialize())
            restarted = GlobalMemoryStore(path)
            self.assertEqual(serialized, restarted.serialize())


if __name__ == "__main__":
    unittest.main()
