"""Smoke tests for the Part 5 memory schemas and state."""

from datetime import UTC, datetime
import unittest

from qwen3_coder_next.memory import (
    MEMORY_SCHEMA_VERSION,
    GlobalPattern,
    MalformedMemorySerializedDataError,
    MemoryEvent,
    MemoryItem,
    MemoryQuery,
    MemoryRevision,
    MemoryResult,
    MemorySerializer,
    MemoryState,
    MemoryTier,
    ProjectDecision,
    RetentionPolicy,
    SessionSummary,
    deserialize_memory_item,
    deserialize_memory_state,
    serialize_memory_state,
)


class MemoryStep1SmokeTest(unittest.TestCase):
    """Verify the Part 5 memory schema and state foundation."""

    def test_memory_contracts_can_be_created(self) -> None:
        """Create the memory contract objects."""

        timestamp = datetime.fromtimestamp(0, UTC)
        item = MemoryItem(
            memory_id="mem-001",
            tier=MemoryTier.PROJECT,
            subject="Keep worktree-based refactors isolated",
            content="Use isolated worktrees for risky refactors.",
            source="architecture-note",
            timestamp=timestamp,
            confidence="high",
            tags=("worktree", "safety"),
            references=("task-42",),
        )
        query = MemoryQuery(
            query_text="How do we handle risky refactors?",
            tier_hint=MemoryTier.PROJECT,
            project_id="project-001",
            session_id="session-001",
            filters={"kind": "decision"},
            top_k=5,
        )
        result = MemoryResult(
            item=item,
            score=0.95,
            rationale="Matches the refactor-safety policy.",
            retrieval_source="project-store",
        )
        summary = SessionSummary(
            session_id="session-001",
            goal="Stabilize the refactor workflow.",
            outcomes=("isolated worktrees adopted",),
            decisions=("use worktrees for risky changes",),
            open_questions=("how to promote decisions?",),
        )
        decision = ProjectDecision(
            project_id="project-001",
            decision="Use worktrees for risky refactors.",
            rationale="Reduces accidental workspace mutation.",
            alternatives=("direct edits",),
            version=1,
        )
        pattern = GlobalPattern(
            pattern_name="Isolated refactors",
            applicability="Large or risky edits",
            evidence=("refactor-incident-17",),
            caveats=("requires additional disk space",),
        )
        event = MemoryEvent(
            event_type="memory_item_appended",
            actor="tester",
            payload={"memory_id": "mem-001"},
            references=("task-42",),
            status="recorded",
        )
        policy = RetentionPolicy(
            tier=MemoryTier.SESSION,
            keep_days=30,
            promote_on_signal=("decision_finalized",),
            prune_on_signal=("session_closed",),
        )

        self.assertEqual(item.memory_id, "mem-001")
        self.assertEqual(query.top_k, 5)
        self.assertEqual(result.item, item)
        self.assertEqual(summary.session_id, "session-001")
        self.assertEqual(decision.version, 1)
        self.assertEqual(pattern.pattern_name, "Isolated refactors")
        self.assertEqual(event.status, "recorded")
        self.assertEqual(policy.tier, MemoryTier.SESSION)

    def test_deterministic_serialization_round_trip(self) -> None:
        """Serialize and deserialize memory artifacts deterministically."""

        serializer = MemorySerializer()
        item = MemoryItem(
            memory_id="mem-002",
            tier=MemoryTier.SESSION,
            subject="Session recap",
            content="Summarize the last session.",
            source="session-note",
            confidence="medium",
            tags=("session", "recap"),
            references=("session-001",),
        )
        state = MemoryState(
            state_id="memory-state-001",
            memory_items=(item,),
            session_summaries=(
                SessionSummary(
                    session_id="session-001",
                    goal="Summarize work.",
                    outcomes=("done",),
                    decisions=("preserve provenance",),
                    open_questions=(),
                ),
            ),
            project_decisions=(
                ProjectDecision(
                    project_id="project-001",
                    decision="Keep memory contracts explicit.",
                    rationale="Stable contracts are easier to evolve.",
                    alternatives=("ad hoc fields",),
                    version=2,
                ),
            ),
            global_patterns=(
                GlobalPattern(
                    pattern_name="Provenance first",
                    applicability="All durable memory records",
                    evidence=("memory-001",),
                    caveats=("none",),
                ),
            ),
            memory_events=(
                MemoryEvent(
                    event_type="memory_state_created",
                    actor="tester",
                    payload={"state_id": "memory-state-001"},
                    references=("memory-state-001",),
                    status="recorded",
                ),
            ),
            retention_policy=RetentionPolicy(
                tier=MemoryTier.PROJECT,
                keep_days=90,
                promote_on_signal=("project_decision",),
                prune_on_signal=("stale",),
            ),
        )

        serialized_once = serializer.serialize(item)
        serialized_twice = serializer.serialize(item)
        self.assertEqual(serialized_once, serialized_twice)
        self.assertEqual(serializer.deserialize_item(serialized_once), item)

        serialized_state = serialize_memory_state(state)
        self.assertEqual(serialized_state, serialize_memory_state(state))
        self.assertEqual(deserialize_memory_state(serialized_state), state)
        self.assertEqual(state.to_dict()["memory_items"][0]["schema_version"], MEMORY_SCHEMA_VERSION)
        self.assertEqual(state.to_dict()["state_version"], 1)

    def test_memory_state_append_first_evolution(self) -> None:
        """Append memory records without mutating the original snapshot."""

        state = MemoryState(state_id="memory-state-002")
        item = MemoryItem(
            memory_id="mem-003",
            tier=MemoryTier.WORKING,
            subject="Working context",
            content="Keep the current task context available.",
            source="runtime",
            confidence="low",
        )

        evolved = state.append_memory_item(item)

        self.assertEqual(state.memory_items, ())
        self.assertEqual(evolved.memory_items, (item,))
        self.assertEqual(evolved.state_version, 2)
        self.assertEqual(evolved.revision_history[0].revision_id, "memory-state-002-rev-0002")
        self.assertEqual(evolved.revision_history[0].summary, "memory item appended")
        self.assertEqual(evolved.updated_at, datetime.fromtimestamp(0, UTC))

    def test_backward_compatible_deserialization_and_malformed_payloads(self) -> None:
        """Support expected legacy aliases and reject malformed payloads."""

        item = deserialize_memory_item(
            {
                "id": "mem-004",
                "tier": "global",
                "subject": "Cross-project pattern",
                "content": "Use explicit contracts.",
                "source": "migration-note",
                "timestamp": datetime.fromtimestamp(0, UTC).isoformat(),
                "confidence": "high",
                "tags": ["contracts"],
                "references": ["migration-001"],
            }
        )
        state = deserialize_memory_state(
            {
                "state_id": "memory-state-003",
                "items": [item.to_dict()],
                "created_at": datetime.fromtimestamp(0, UTC).isoformat(),
                "updated_at": datetime.fromtimestamp(0, UTC).isoformat(),
            }
        )

        self.assertEqual(item.memory_id, "mem-004")
        self.assertEqual(state.memory_items, (item,))
        self.assertEqual(state.state_version, 1)

        with self.assertRaises(MalformedMemorySerializedDataError):
            deserialize_memory_state("{not-json")

        with self.assertRaises(MalformedMemorySerializedDataError):
            deserialize_memory_state(
                {
                    "state_id": "memory-state-004",
                    "memory_items": "not-a-collection",
                }
            )

        with self.assertRaises(ValueError):
            MemoryQuery(query_text="?", top_k=0)

        with self.assertRaises(ValueError):
            MemoryRevision(revision_id="", revision_number=1, summary="bad")


if __name__ == "__main__":
    print("Memory Step 1 smoke tests passed.")
    unittest.main(verbosity=2)
