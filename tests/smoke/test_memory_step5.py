
"""Smoke tests for Part 5 Step 5 retrieval and ranking."""

from datetime import UTC, datetime, timedelta
import unittest

from qwen3_coder_next.memory import (
    MalformedMemorySerializedDataError,
    MemoryItem,
    MemoryQuery,
    MemoryRetriever,
    MemoryResult,
    MemorySerializer,
    MemoryState,
    MemoryTier,
    ProjectDecision,
    ProjectMemoryStore,
    SessionMemoryStore,
    SessionSummary,
)


class MemoryStep5SmokeTest(unittest.TestCase):
    """Verify deterministic retrieval and ranking across memory tiers."""

    def _item(
        self,
        memory_id: str,
        tier: MemoryTier,
        subject: str,
        content: str,
        source: str,
        timestamp: datetime,
    ) -> MemoryItem:
        return MemoryItem(
            memory_id=memory_id,
            tier=tier,
            subject=subject,
            content=content,
            source=source,
            timestamp=timestamp,
            confidence="high",
            tags=("cache", "retrieval"),
            references=("task-42",),
        )

    def test_deterministic_ranking_and_tier_hint_preference(self) -> None:
        retriever = MemoryRetriever()
        base = datetime.fromtimestamp(0, UTC)
        working = MemoryState(
            state_id="task-001-working",
            memory_items=(
                self._item(
                    "working-001",
                    MemoryTier.WORKING,
                    "Cache invalidation fix",
                    "Fix the cache invalidation path.",
                    "runtime-working-memory",
                    base + timedelta(seconds=20),
                ),
            ),
        )
        session_store = SessionMemoryStore()
        session_store.create_session_state(
            MemoryState(
                state_id="session-001",
                memory_items=(
                    self._item(
                        "session-001-item",
                        MemoryTier.SESSION,
                        "Cache invalidation fix",
                        "Fix the cache invalidation path.",
                        "session-store",
                        base + timedelta(seconds=10),
                    ),
                ),
            )
        )
        project_store = ProjectMemoryStore()
        project_store.create_project_state(
            MemoryState(
                state_id="project-001",
                project_decisions=(
                    ProjectDecision(
                        project_id="project-001",
                        decision="Keep cache invalidation deterministic.",
                        rationale="Prevents stale state from leaking.",
                        alternatives=("best-effort invalidation",),
                        version=1,
                    ),
                ),
            )
        )

        query = MemoryQuery(
            query_text="cache invalidation fix",
            tier_hint=MemoryTier.WORKING,
            project_id="project-001",
            session_id="session-001",
            top_k=3,
        )

        first = retriever.retrieve(
            query,
            working_memory=working,
            session_store=session_store,
            project_store=project_store,
        )
        second = retriever.retrieve(
            query,
            working_memory=working,
            session_store=session_store,
            project_store=project_store,
        )

        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        self.assertEqual(first[0].item.memory_id, "working-001")
        self.assertEqual(first[0].item.tier, MemoryTier.WORKING)
        self.assertTrue(first[1].retrieval_source.startswith("session-store:"))
        self.assertTrue(first[2].retrieval_source.startswith("project-store:"))

    def test_deduplication_and_provenance_preservation(self) -> None:
        retriever = MemoryRetriever()
        item = self._item(
            "duplicate-001",
            MemoryTier.SESSION,
            "Bug fix memory",
            "The documented bug fix should be retrievable with references.",
            "session-store",
            datetime.fromtimestamp(0, UTC),
        )
        session_store = SessionMemoryStore()
        session_store.create_session_state(MemoryState(state_id="session-002", memory_items=(item,)))
        project_store = ProjectMemoryStore()
        project_store.create_project_state(MemoryState(state_id="project-002", memory_items=(item,)))

        results = retriever.retrieve(
            MemoryQuery(query_text="bug fix retrievable references", top_k=10),
            session_store=session_store,
            project_store=project_store,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].item, item)
        self.assertTrue(results[0].retrieval_source.startswith(("session-store:", "project-store:")))

        serializer = MemorySerializer()
        serialized = serializer.serialize(results[0])
        self.assertEqual(serializer.deserialize_result(serialized), results[0])

    def test_read_only_behavior_and_malformed_input_handling(self) -> None:
        retriever = MemoryRetriever()
        session_store = SessionMemoryStore()
        project_store = ProjectMemoryStore()
        session_store.create_session_state(
            MemoryState(
                state_id="session-003",
                session_summaries=(
                    SessionSummary(
                        session_id="session-003",
                        goal="Retain bug fix history.",
                        outcomes=("bug fix documented",),
                        decisions=("keep provenance",),
                        open_questions=(),
                    ),
                ),
            )
        )
        project_store.create_project_state(
            MemoryState(
                state_id="project-003",
                project_decisions=(
                    ProjectDecision(
                        project_id="project-003",
                        decision="Persist bug-fix decisions.",
                        rationale="Allows later retrieval.",
                        alternatives=(),
                        version=2,
                    ),
                ),
            )
        )
        session_before = session_store.serialize()
        project_before = project_store.serialize()

        results = retriever.retrieve(
            MemoryQuery(query_text="bug fix history", project_id="project-003", session_id="session-003", top_k=5),
            session_store=session_store,
            project_store=project_store,
        )

        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(session_store.serialize(), session_before)
        self.assertEqual(project_store.serialize(), project_before)
        self.assertTrue(results[0].item.content)

        with self.assertRaises(ValueError):
            retriever.retrieve("bad-query")

        with self.assertRaises(ValueError):
            MemoryQuery(query_text="x", top_k=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
