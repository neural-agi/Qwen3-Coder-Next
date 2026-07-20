"""Smoke tests for Part 4 Step 6 research packet assembly."""

from __future__ import annotations

from datetime import UTC, datetime
import unittest

from qwen3_coder_next.research import (
    EvidenceFreshness,
    EvidenceItem,
    EvidenceProvenance,
    MalformedResearchPacketInputError,
    ResearchBudget,
    ResearchEvidenceNormalizationResult,
    ResearchNextAction,
    ResearchPacket,
    ResearchPacketAssembler,
    ResearchRequest,
    ResearchTaskType,
    SourcePolicy,
    SourceType,
    assemble_research_packet,
)


class ResearchStep6SmokeTest(unittest.TestCase):
    """Verify deterministic research packet assembly."""

    def _request(self) -> ResearchRequest:
        return ResearchRequest(
            request_id="req-packet-001",
            task_type=ResearchTaskType.INVESTIGATION,
            target_repo="Qwen-3-Coder-Next",
            query_text="assemble the research packet",
            budget=ResearchBudget(source_limit=2, snippet_limit=200),
        )

    def _policy(self) -> SourcePolicy:
        return SourcePolicy(
            allowed_sources=(SourceType.REPO_FILE, SourceType.DOC, SourceType.LOG),
            preferred_sources=(SourceType.REPO_FILE, SourceType.DOC),
            blocked_sources=(),
            source_rank_weights={"repo_file": 1.0, "doc": 0.8, "log": 0.6},
            max_evidence_items=2,
            max_snippet_chars=200,
        )

    def _normalized_evidence(self) -> ResearchEvidenceNormalizationResult:
        first = EvidenceItem(
            evidence_id="evi-001",
            source_type=SourceType.REPO_FILE,
            source_ref="src/research/packet.py",
            excerpt="assemble the research packet",
            relevance_score=0.95,
            confidence=0.9,
            freshness=EvidenceFreshness.CURRENT,
            provenance=EvidenceProvenance(
                tool="scanner",
                timestamp=datetime.fromtimestamp(0, UTC),
                line_range=(1, 3),
            ),
        )
        second = EvidenceItem(
            evidence_id="evi-002",
            source_type=SourceType.DOC,
            source_ref="docs/research.md",
            excerpt="packet assembly context",
            relevance_score=0.8,
            confidence=0.75,
            freshness=EvidenceFreshness.UNKNOWN,
            provenance=EvidenceProvenance(
                tool="fetcher",
                timestamp=datetime.fromtimestamp(0, UTC),
            ),
        )
        third = EvidenceItem(
            evidence_id="evi-003",
            source_type=SourceType.LOG,
            source_ref="logs/research.log",
            excerpt="supplemental evidence",
            relevance_score=0.7,
            confidence=0.7,
            freshness=EvidenceFreshness.STALE,
            provenance=EvidenceProvenance(
                tool="fetcher",
                timestamp=datetime.fromtimestamp(0, UTC),
            ),
        )
        return ResearchEvidenceNormalizationResult(evidence_items=(first, second, third))

    def test_packet_assembly(self) -> None:
        """Assemble a packet that preserves request, policy, and evidence context."""

        request = self._request()
        policy = self._policy()
        normalized = self._normalized_evidence()

        packet = assemble_research_packet(request, normalized, source_policy=policy)

        self.assertIsInstance(packet, ResearchPacket)
        self.assertEqual(packet.request_id, request.request_id)
        self.assertEqual(packet.evidence, normalized.evidence_items[:2])
        self.assertEqual(packet.recommended_next_action, ResearchNextAction.CODE)
        self.assertEqual(packet.citations, ("src/research/packet.py:1-3", "docs/research.md"))
        self.assertEqual(packet.artifacts[0], f"request:{request.request_id}")
        self.assertTrue(packet.artifacts[1].startswith("source-policy:"))
        self.assertEqual(packet.artifacts[2:], ("evidence:evi-001", "evidence:evi-002"))
        self.assertIn("assemble the research packet", packet.summary)
        self.assertIn("Qwen-3-Coder-Next", packet.summary)

    def test_deterministic_packet_output(self) -> None:
        """Return the same packet for equivalent inputs."""

        request = self._request()
        policy = self._policy()
        normalized = self._normalized_evidence()

        first = assemble_research_packet(request, normalized, source_policy=policy)
        second = ResearchPacketAssembler().assemble(request, normalized, source_policy=policy)

        self.assertEqual(first, second)
        self.assertEqual(ResearchPacket.from_dict(first.to_dict()), first)

    def test_evidence_selection_and_provenance_preservation(self) -> None:
        """Preserve evidence ordering while applying the configured limit."""

        request = self._request()
        policy = self._policy()
        normalized = self._normalized_evidence()

        packet = ResearchPacketAssembler().assemble(request, normalized, source_policy=policy)

        self.assertEqual(tuple(item.provenance.tool for item in packet.evidence), ("scanner", "fetcher"))
        self.assertEqual(tuple(item.evidence_id for item in packet.evidence), ("evi-001", "evi-002"))
        self.assertEqual(packet.confidence, 0.85)

    def test_malformed_input_handling(self) -> None:
        """Reject malformed packet assembly inputs."""

        request = self._request()
        policy = self._policy()

        with self.assertRaises(MalformedResearchPacketInputError):
            assemble_research_packet("bad", self._normalized_evidence(), source_policy=policy)  # type: ignore[arg-type]
        with self.assertRaises(MalformedResearchPacketInputError):
            ResearchPacketAssembler().assemble(request, "bad", source_policy=policy)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
