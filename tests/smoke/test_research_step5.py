"""Smoke tests for Part 4 Step 5 evidence normalization and ranking."""

from __future__ import annotations

from datetime import UTC, datetime
import unittest

from qwen3_coder_next.research import (
    DocumentFetcher,
    EvidenceFreshness,
    EvidenceItem,
    EvidenceProvenance,
    ErrorFetcher,
    LogFetcher,
    MalformedResearchEvidenceError,
    ResearchBudget,
    ResearchEvidenceNormalizationResult,
    ResearchFetchResult,
    ResearchRequest,
    ResearchRequestNormalizer,
    ResearchTaskType,
    SourcePolicy,
    SourceType,
    normalize_research_evidence,
)


class ResearchStep5SmokeTest(unittest.TestCase):
    """Verify evidence normalization, ranking, and deduplication."""

    def _request(self) -> ResearchRequest:
        return ResearchRequest(
            request_id="req-evidence-001",
            task_type=ResearchTaskType.INVESTIGATION,
            target_repo="Qwen-3-Coder-Next",
            query_text="alpha trace",
            budget=ResearchBudget(source_limit=3, snippet_limit=200),
        )

    def _policy(self) -> SourcePolicy:
        return SourcePolicy(
            allowed_sources=(SourceType.DOC, SourceType.LOG, SourceType.ERROR_ARTIFACT),
            preferred_sources=(SourceType.LOG, SourceType.DOC),
            blocked_sources=(),
            source_rank_weights={
                "log": 1.0,
                "doc": 0.8,
                "error_artifact": 0.4,
            },
            max_evidence_items=3,
            max_snippet_chars=200,
        )

    def test_evidence_normalization_and_ranking(self) -> None:
        """Normalize snippets and rank by task relevance and freshness."""

        request = self._request()
        policy = self._policy()
        evidence = (
            EvidenceItem(
                evidence_id="e-003",
                source_type=SourceType.ERROR_ARTIFACT,
                source_ref="errors/failure.txt",
                excerpt="alpha trace failed",
                relevance_score=0.4,
                confidence=0.7,
                freshness=EvidenceFreshness.UNKNOWN,
                provenance=EvidenceProvenance(tool="error-fetcher", timestamp=datetime.fromtimestamp(0, UTC)),
            ),
            EvidenceItem(
                evidence_id="e-001",
                source_type=SourceType.DOC,
                source_ref="docs/guide.md",
                excerpt="  alpha trace\nsecond line  ",
                relevance_score=0.8,
                confidence=0.6,
                freshness=EvidenceFreshness.CURRENT,
                provenance=EvidenceProvenance(
                    tool="doc-fetcher",
                    timestamp=datetime.fromtimestamp(0, UTC),
                    line_range=(2, 4),
                ),
            ),
            EvidenceItem(
                evidence_id="e-002",
                source_type=SourceType.LOG,
                source_ref="logs/app.log",
                excerpt="alpha trace\nlog line",
                relevance_score=0.9,
                confidence=0.9,
                freshness=EvidenceFreshness.CURRENT,
                provenance=EvidenceProvenance(tool="log-fetcher", timestamp=datetime.fromtimestamp(0, UTC)),
            ),
        )

        result = normalize_research_evidence(evidence, request=request, source_policy=policy)
        repeated = normalize_research_evidence(evidence, request=request, source_policy=policy)

        self.assertIsInstance(result, ResearchEvidenceNormalizationResult)
        self.assertEqual(result, repeated)
        self.assertEqual(
            tuple(item.source_ref for item in result.evidence_items),
            ("logs/app.log", "docs/guide.md", "errors/failure.txt"),
        )
        self.assertEqual(tuple(item.provenance.tool for item in result.evidence_items), ("log-fetcher", "doc-fetcher", "error-fetcher"))
        self.assertEqual(result.evidence_items[1].excerpt, "alpha trace\nsecond line")
        self.assertEqual(result.evidence_items[1].provenance.line_range, (2, 4))
        self.assertEqual(ResearchEvidenceNormalizationResult.from_dict(result.to_dict()), result)

    def test_deduplication_and_freshness_handling(self) -> None:
        """Deduplicate near-identical evidence while preferring fresher items."""

        request = self._request()
        policy = self._policy()
        duplicate_a = EvidenceItem(
            evidence_id="dup-a",
            source_type=SourceType.DOC,
            source_ref="docs/dup.md",
            excerpt="alpha trace\nshared",
            relevance_score=0.5,
            confidence=0.5,
            freshness=EvidenceFreshness.STALE,
            provenance=EvidenceProvenance(tool="doc-fetcher", timestamp=datetime.fromtimestamp(0, UTC)),
        )
        duplicate_b = EvidenceItem(
            evidence_id="dup-b",
            source_type=SourceType.DOC,
            source_ref="docs/dup.md",
            excerpt=" alpha trace \nshared  ",
            relevance_score=0.7,
            confidence=0.8,
            freshness=EvidenceFreshness.CURRENT,
            provenance=EvidenceProvenance(tool="doc-fetcher", timestamp=datetime.fromtimestamp(0, UTC)),
        )

        result = normalize_research_evidence((duplicate_a, duplicate_b), request=request, source_policy=policy)

        self.assertEqual(len(result.evidence_items), 1)
        self.assertEqual(result.evidence_items[0].evidence_id, "dup-b")
        self.assertEqual(result.evidence_items[0].freshness, EvidenceFreshness.CURRENT)
        self.assertEqual(result.evidence_items[0].excerpt, "alpha trace\nshared")

    def test_research_fetch_and_scan_results_are_flattened(self) -> None:
        """Accept existing research result containers as evidence sources."""

        request = self._request()
        policy = self._policy()
        base_item = EvidenceItem(
            evidence_id="base-001",
            source_type=SourceType.LOG,
            source_ref="logs/base.log",
            excerpt="alpha trace",
            relevance_score=0.9,
            confidence=0.9,
            freshness=EvidenceFreshness.CURRENT,
            provenance=EvidenceProvenance(tool="log-fetcher", timestamp=datetime.fromtimestamp(0, UTC)),
        )
        fetch_result = ResearchFetchResult(
            request_id="req-evidence-001",
            source_handles=(),
            evidence_items=(base_item,),
        )
        scan_result = DocumentFetcher().fetch(request, policy, [])
        combined = normalize_research_evidence((fetch_result, scan_result), request=request, source_policy=policy)

        self.assertEqual(combined.evidence_items[0].source_ref, "logs/base.log")
        self.assertEqual(ResearchEvidenceNormalizationResult.from_dict(combined.to_dict()), combined)

    def test_malformed_input_handling(self) -> None:
        """Reject malformed inputs and unsupported evidence objects."""

        request = self._request()
        policy = self._policy()

        with self.assertRaises(MalformedResearchEvidenceError):
            normalize_research_evidence("bad")  # type: ignore[arg-type]
        with self.assertRaises(MalformedResearchEvidenceError):
            normalize_research_evidence((object(),), request=request, source_policy=policy)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
