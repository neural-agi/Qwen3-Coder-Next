"""Smoke tests for Part 4 Step 1 research schemas and state."""

from datetime import UTC, datetime
import unittest

from qwen3_coder_next.research import (
    EvidenceFreshness,
    EvidenceItem,
    EvidenceProvenance,
    ResearchBudget,
    ResearchNextAction,
    ResearchPacket,
    ResearchRequest,
    ResearchState,
    ResearchStateStatus,
    ResearchTaskType,
    SourceHandle,
    SourcePolicy,
    SourceType,
)


class ResearchStep1SmokeTest(unittest.TestCase):
    """Verify schema creation, serialization, and state behavior."""

    def test_schema_creation_and_round_trip(self) -> None:
        """Create the research schemas and round-trip them through dict form."""

        request = ResearchRequest(
            request_id="req-001",
            task_type=ResearchTaskType.INVESTIGATION,
            target_repo="Qwen-3-Coder-Next",
            query_text="Understand the research layer boundary",
            constraints=("read-only", "local-only"),
            hints=("planning output", "runtime flow"),
            budget=ResearchBudget(time_ms=12_000, source_limit=8, snippet_limit=400),
        )
        source_handle = SourceHandle(
            source_id="src-001",
            source_type=SourceType.REPO_FILE,
            source_ref="src/qwen3_coder_next/planning/schemas.py",
            display_name="planning schemas",
            metadata={"scope": "foundation"},
        )
        provenance = EvidenceProvenance(
            tool="repo-scanner",
            timestamp=datetime.fromtimestamp(0, UTC),
            line_range=(1, 12),
        )
        evidence = EvidenceItem(
            evidence_id="evi-001",
            source_type=SourceType.REPO_FILE,
            source_ref=source_handle.source_ref,
            excerpt="Research layer consumes structured objects.",
            relevance_score=0.95,
            confidence=0.9,
            freshness=EvidenceFreshness.CURRENT,
            provenance=provenance,
        )
        packet = ResearchPacket(
            request_id="req-001",
            summary="Research contracts established.",
            evidence=(evidence,),
            recommended_next_action=ResearchNextAction.CODE,
            confidence=0.88,
            open_questions=("Confirm cache boundaries.",),
            citations=("src/qwen3_coder_next/planning/schemas.py:1-12",),
            artifacts=("artifacts/research/req-001.json",),
        )
        policy = SourcePolicy(
            allowed_sources=(SourceType.REPO_FILE, SourceType.DOC),
            preferred_sources=(SourceType.REPO_FILE,),
            blocked_sources=(SourceType.ERROR_ARTIFACT,),
            source_rank_weights={"repo_file": 1.0, "doc": 0.8},
            max_evidence_items=10,
            max_snippet_chars=600,
            cache_ttl_minutes=30,
        )

        self.assertEqual(ResearchRequest.from_dict(request.to_dict()), request)
        self.assertEqual(SourceHandle.from_dict(source_handle.to_dict()), source_handle)
        self.assertEqual(EvidenceProvenance.from_dict(provenance.to_dict()), provenance)
        self.assertEqual(EvidenceItem.from_dict(evidence.to_dict()), evidence)
        self.assertEqual(ResearchPacket.from_dict(packet.to_dict()), packet)
        self.assertEqual(SourcePolicy.from_dict(policy.to_dict()), policy)

    def test_state_creation_and_updates(self) -> None:
        """Create research state and verify immutable update behavior."""

        request = ResearchRequest(
            request_id="req-002",
            task_type=ResearchTaskType.BUG,
            target_repo="Qwen-3-Coder-Next",
            query_text="Investigate a docs mismatch",
        )
        source_handle = SourceHandle(
            source_id="src-002",
            source_type=SourceType.DOC,
            source_ref="docs/architecture.md",
        )
        evidence = EvidenceItem(
            evidence_id="evi-002",
            source_type=SourceType.DOC,
            source_ref="docs/architecture.md",
            excerpt="Research state records evidence append-only.",
            relevance_score=0.8,
            confidence=0.75,
            freshness=EvidenceFreshness.UNKNOWN,
            provenance=EvidenceProvenance(tool="doc-loader", timestamp=datetime.fromtimestamp(0, UTC)),
        )
        packet = ResearchPacket(
            request_id="req-002",
            summary="Research packet ready.",
            evidence=(evidence,),
            recommended_next_action=ResearchNextAction.CLARIFY,
            confidence=0.5,
        )
        policy = SourcePolicy(allowed_sources=(SourceType.DOC,), max_evidence_items=5)
        state = ResearchState(state_id="research-state-001")

        updated = (
            state.with_request(request)
            .with_source_policy(policy)
            .with_selected_sources((source_handle,))
            .add_evidence_item(evidence)
            .with_research_packet(packet)
            .with_status(ResearchStateStatus.HANDOFF_READY)
        )

        self.assertEqual(state.state_version, 1)
        self.assertEqual(updated.state_id, "research-state-001")
        self.assertEqual(updated.current_request, request)
        self.assertEqual(updated.source_policy, policy)
        self.assertEqual(updated.selected_sources, (source_handle,))
        self.assertEqual(updated.evidence_items, (evidence,))
        self.assertEqual(updated.research_packet, packet)
        self.assertEqual(updated.status, ResearchStateStatus.HANDOFF_READY)
        self.assertEqual(len(updated.revision_history), 6)
        self.assertEqual(updated.revision_history[0].revision_id, "research-state-001-rev-0002")
        self.assertEqual(updated.revision_history[-1].revision_number, 7)
        self.assertEqual(ResearchState.from_dict(updated.to_dict()), updated)

    def test_stable_identifiers_and_revision_behavior(self) -> None:
        """Keep state identifiers and revision numbering stable."""

        state = ResearchState(state_id="research-state-002")

        first = state.record_revision("initial note")
        second = first.record_revision("second note")

        self.assertEqual(first.revision_history[0].revision_id, "research-state-002-rev-0002")
        self.assertEqual(second.revision_history[-1].revision_id, "research-state-002-rev-0003")
        self.assertEqual(first.state_id, second.state_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
