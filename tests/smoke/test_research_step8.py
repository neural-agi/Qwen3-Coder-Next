"""Smoke tests for Part 4 Step 8 research observability and failure paths."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.research import (
    ResearchNextAction,
    ResearchPacket,
    ResearchPipeline,
    ResearchPipelineResult,
    ResearchRequest,
    ResearchStateStatus,
    ResearchTaskType,
    SourcePolicy,
    SourceType,
)


class ResearchStep8SmokeTest(unittest.TestCase):
    """Verify deterministic observability, traceability, and fallback signaling."""

    def _request(self) -> ResearchRequest:
        return ResearchRequest(
            request_id="req-observability-001",
            task_type=ResearchTaskType.INVESTIGATION,
            target_repo="Qwen-3-Coder-Next",
            query_text="observability integration",
        )

    def _policy(self) -> SourcePolicy:
        return SourcePolicy(
            allowed_sources=(
                SourceType.REPO_FILE,
                SourceType.DOC,
                SourceType.LOG,
                SourceType.ERROR_ARTIFACT,
            ),
            preferred_sources=(SourceType.REPO_FILE, SourceType.DOC),
            blocked_sources=(),
            source_rank_weights={
                "repo_file": 1.0,
                "doc": 0.8,
                "log": 0.7,
                "error_artifact": 0.5,
            },
            max_evidence_items=4,
            max_snippet_chars=240,
        )

    def test_stage_transitions_and_logging(self) -> None:
        """Emit structured stage logs and trace records in deterministic order."""

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_file = root / "research.py"
            doc_file = root / "notes.md"
            log_file = root / "app.log"
            error_file = root / "error.txt"
            repo_file.write_text("observability integration\nalpha\n", encoding="utf-8")
            doc_file.write_text("observability docs\n", encoding="utf-8")
            log_file.write_text("observability logs\n", encoding="utf-8")
            error_file.write_text("RuntimeError: observability\n", encoding="utf-8")

            pipeline = ResearchPipeline()
            with self.assertLogs("qwen3_coder_next.research.pipeline", level="INFO") as captured:
                result = pipeline.run(
                    self._request(),
                    source_policy=self._policy(),
                    repository_root=root,
                    document_refs=(doc_file,),
                    log_artifacts=(log_file,),
                    error_artifacts=(error_file,),
                )

            self.assertIsInstance(result, ResearchPipelineResult)
            self.assertEqual(
                tuple((item.stage_name, item.event) for item in result.observability.stage_transitions),
                (
                    ("repository_scan", "started"),
                    ("repository_scan", "completed"),
                    ("document_fetch", "started"),
                    ("document_fetch", "completed"),
                    ("log_fetch", "started"),
                    ("log_fetch", "completed"),
                    ("error_fetch", "started"),
                    ("error_fetch", "completed"),
                    ("evidence_normalization", "started"),
                    ("evidence_normalization", "completed"),
                    ("packet_assembly", "started"),
                    ("packet_assembly", "completed"),
                ),
            )
            self.assertEqual(result.observability.metrics.executed_stage_count, 6)
            self.assertEqual(result.observability.metrics.skipped_stage_count, 0)
            self.assertFalse(result.observability.clarification_required)
            self.assertIsNone(result.observability.failure_record)
            self.assertIn("Research stage started", "\n".join(captured.output))
            self.assertIn("Research stage completed", "\n".join(captured.output))

    def test_clarification_path_and_failure_record(self) -> None:
        """Signal the clarification path when evidence is insufficient."""

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            root.mkdir(parents=True, exist_ok=True)

            pipeline = ResearchPipeline()
            result = pipeline.run(
                self._request(),
                source_policy=SourcePolicy(
                    allowed_sources=(SourceType.REPO_FILE,),
                    preferred_sources=(SourceType.REPO_FILE,),
                    blocked_sources=(),
                    source_rank_weights={"repo_file": 1.0},
                    max_evidence_items=4,
                    max_snippet_chars=240,
                ),
                repository_root=root,
                document_refs=(),
                log_artifacts=(),
                error_artifacts=(),
            )

            self.assertTrue(result.observability.clarification_required)
            self.assertIsNotNone(result.observability.failure_record)
            self.assertEqual(
                result.observability.fallback_decision,
                result.research_packet.recommended_next_action,
            )
            self.assertEqual(result.observability.failure_record.stage_name, "packet_assembly")
            self.assertEqual(result.observability.failure_record.state_status, ResearchStateStatus.NEEDS_CLARIFICATION)
            self.assertEqual(result.research_state.status, ResearchStateStatus.NEEDS_CLARIFICATION)
            self.assertEqual(result.research_packet.recommended_next_action, ResearchNextAction.EXPAND_RESEARCH)

    def test_observability_round_trip_and_determinism(self) -> None:
        """Round-trip the pipeline result and preserve observability deterministically."""

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "research.py").write_text("observability integration\n", encoding="utf-8")

            pipeline = ResearchPipeline()
            first = pipeline.run(
                self._request(),
                source_policy=self._policy(),
                repository_root=root,
            )
            second = pipeline.run(
                self._request(),
                source_policy=self._policy(),
                repository_root=root,
            )
            round_trip = ResearchPipelineResult.from_dict(first.to_dict())

            self.assertEqual(first, second)
            self.assertEqual(first.observability, second.observability)
            self.assertEqual(round_trip, first)
            self.assertEqual(round_trip.observability.to_dict(), first.observability.to_dict())

    def test_read_only_behavior(self) -> None:
        """Leave repository contents unchanged during observability-enabled runs."""

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_file = root / "research.py"
            repo_file.write_text("observability integration\n", encoding="utf-8")
            before = repo_file.read_text(encoding="utf-8")

            result = ResearchPipeline().run(
                self._request(),
                source_policy=self._policy(),
                repository_root=root,
            )

            after = repo_file.read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertIsInstance(result.observability.metrics.packet_confidence, float)


if __name__ == "__main__":
    unittest.main(verbosity=2)
