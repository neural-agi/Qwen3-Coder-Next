"""End-to-end integration coverage for Part 5 Step 9."""

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from qwen3_coder_next.memory import (
    GlobalMemoryStore,
    MemoryAuditRecorder,
    MemoryEvent,
    MemoryItem,
    MemoryLifecycleAction,
    MemoryLifecycleActionType,
    MemoryLifecyclePlan,
    MemoryPolicyEngine,
    MemoryQuery,
    MemoryState,
    MemoryTier,
    ProjectMemoryStore,
    RetentionPolicy,
    SessionMemoryStore,
    deserialize_memory_state,
    serialize_memory_state,
)
from qwen3_coder_next.memory.retrieval import MemoryRetriever


class MemoryStep9SmokeTest(unittest.TestCase):
    def _item(self, memory_id: str, *, timestamp: datetime) -> MemoryItem:
        return MemoryItem(
            memory_id=memory_id,
            tier=MemoryTier.SESSION,
            subject="cache rule",
            content="Use deterministic cache invalidation.",
            source="session",
            timestamp=timestamp,
            confidence="high",
            tags=("cache", "stable"),
            references=("task-9", "source-9"),
            schema_version=2,
        )

    def test_write_read_promote_prune_global_and_audit_flow(self) -> None:
        now = datetime(2026, 1, 31, tzinfo=UTC)
        item = self._item("memory-9", timestamp=now - timedelta(days=1))
        session_state = MemoryState(state_id="session-9").append_memory_item(item).with_retention_policy(
            RetentionPolicy(
                tier=MemoryTier.SESSION,
                keep_days=30,
                promote_on_signal=("promote",),
                prune_on_signal=("prune",),
            )
        )
        recorder = MemoryAuditRecorder()
        session_state = recorder.record_memory_write(session_state, item)

        with TemporaryDirectory() as directory:
            session_store = SessionMemoryStore(Path(directory) / "session.json")
            session_store.create_session_state(session_state)
            results = MemoryRetriever().retrieve(
                MemoryQuery(query_text="deterministic cache", session_id="session-9", top_k=1),
                session_store=session_store,
            )
            self.assertEqual(results[0].item.memory_id, "memory-9")
            self.assertEqual(results[0].item.references, item.references)

            promoted_source = session_state.append_memory_event(
                MemoryEvent(event_type="promote", actor="test", references=(item.memory_id,))
            )
            promoted_state = MemoryPolicyEngine().apply(promoted_source, as_of=now)
            promoted_item = promoted_state.memory_items[0]
            self.assertEqual(promoted_item.tier, MemoryTier.PROJECT)

            project_store = ProjectMemoryStore(Path(directory) / "project.json")
            project_store.create_project_state(MemoryState(state_id="project-9", memory_items=(promoted_item,)))

            global_plan = MemoryLifecyclePlan(
                state_id="project-9",
                as_of=now,
                actions=(
                    MemoryLifecycleAction(
                        MemoryLifecycleActionType.PROMOTE,
                        promoted_item,
                        MemoryTier.GLOBAL,
                        "explicit global promotion",
                    ),
                ),
            )
            global_store = GlobalMemoryStore(Path(directory) / "global.json")
            global_state = global_store.promote_from_plan(global_plan)
            self.assertEqual(global_store.get_global_state(global_state.state_id), global_state)
            self.assertEqual(global_state.memory_items[0].tier, MemoryTier.GLOBAL)

            prunable = MemoryState(state_id="session-prune").append_memory_item(
                self._item("memory-prune", timestamp=now - timedelta(days=31))
            ).with_retention_policy(
                RetentionPolicy(tier=MemoryTier.SESSION, keep_days=30, prune_on_signal=("prune",))
            ).append_memory_event(
                MemoryEvent(event_type="prune", actor="test", references=("memory-prune",))
            )
            pruned = MemoryPolicyEngine().apply(prunable, as_of=now)
            self.assertEqual(pruned.memory_items, ())
            self.assertEqual(pruned.memory_events[-1].event_type, "memory_evicted")

            restarted = GlobalMemoryStore(Path(directory) / "global.json")
            self.assertEqual(restarted.serialize(), global_store.serialize())

        event_types = tuple(event.event_type for event in session_state.memory_events)
        self.assertEqual(event_types, ("memory_write",))
        self.assertEqual(serialize_memory_state(session_state), serialize_memory_state(deserialize_memory_state(serialize_memory_state(session_state))))

    def test_invalid_global_plan_and_invalid_retrieval_are_rejected(self) -> None:
        global_store = GlobalMemoryStore()
        with self.assertRaises(ValueError):
            global_store.promote_from_plan("invalid")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            MemoryRetriever().retrieve("invalid")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
