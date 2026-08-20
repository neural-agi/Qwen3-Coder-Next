"""Smoke tests for Part 5 Step 6 memory lifecycle policies."""

import unittest
from datetime import UTC, datetime, timedelta

from qwen3_coder_next.memory import (
    MemoryEvent,
    MemoryItem,
    MemoryLifecycleActionType,
    MemoryPolicyEngine,
    MemoryState,
    MemoryTier,
    RetentionPolicy,
)


class MemoryStep6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 1, 1, tzinfo=UTC)
        self.item = MemoryItem(
            memory_id="memory-1",
            tier=MemoryTier.SESSION,
            subject="decision",
            content="keep provenance",
            source="test",
            timestamp=self.now - timedelta(days=2),
            references=("citation-1",),
            schema_version=7,
        )
        self.state = MemoryState(state_id="session-1").append_memory_item(self.item).with_retention_policy(
            RetentionPolicy(
                tier=MemoryTier.SESSION,
                keep_days=30,
                promote_on_signal=("promote",),
                prune_on_signal=("prune",),
            )
        )

    def test_promotion_is_deterministic_and_preserves_item_metadata(self) -> None:
        state = self.state.append_memory_event(
            MemoryEvent(event_type="promote", actor="test", references=("memory-1",))
        )
        engine = MemoryPolicyEngine()
        first = engine.plan(state, as_of=self.now)
        second = engine.plan(state, as_of=self.now)
        self.assertEqual(first, second)
        self.assertEqual(first.actions[0].action, MemoryLifecycleActionType.PROMOTE)
        promoted = engine.apply(state, as_of=self.now).memory_items[0]
        self.assertEqual(promoted.tier, MemoryTier.PROJECT)
        self.assertEqual(promoted.references, ("citation-1",))
        self.assertEqual(promoted.schema_version, 7)
        self.assertEqual(state.memory_items[0].tier, MemoryTier.SESSION)

    def test_prune_signal_evicts_deterministically(self) -> None:
        state = self.state.append_memory_event(
            MemoryEvent(event_type="prune", actor="test", references=("memory-1",))
        )
        engine = MemoryPolicyEngine()
        plan = engine.plan(state, as_of=self.now)
        self.assertEqual(plan.actions[0].action, MemoryLifecycleActionType.EVICT)
        updated = engine.apply(state, as_of=self.now)
        self.assertEqual(updated.memory_items, ())
        self.assertGreater(updated.state_version, state.state_version)
        self.assertEqual(updated.memory_events[-1].event_type, "memory_evicted")

    def test_event_status_is_not_treated_as_a_signal(self) -> None:
        state = self.state.append_memory_event(
            MemoryEvent(
                event_type="unrelated",
                actor="test",
                status="promote",
                references=("memory-1",),
            )
        )
        plan = MemoryPolicyEngine().plan(state, as_of=self.now)
        self.assertEqual(plan.actions, ())

    def test_exact_cutoff_is_retained_and_global_items_are_unchanged(self) -> None:
        cutoff_item = MemoryItem(
            memory_id="cutoff",
            tier=MemoryTier.SESSION,
            subject="boundary",
            content="boundary",
            source="test",
            timestamp=self.now - timedelta(days=30),
        )
        global_item = MemoryItem(
            memory_id="global",
            tier=MemoryTier.GLOBAL,
            subject="global",
            content="global",
            source="test",
            timestamp=self.now - timedelta(days=1000),
        )
        state = self.state.append_memory_item(cutoff_item).append_memory_item(global_item)
        plan = MemoryPolicyEngine().plan(state, as_of=self.now)
        self.assertEqual(plan.actions, ())

    def test_no_policy_returns_original_state(self) -> None:
        state = MemoryState(state_id="empty")
        self.assertIs(MemoryPolicyEngine().apply(state), state)


if __name__ == "__main__":
    unittest.main()
