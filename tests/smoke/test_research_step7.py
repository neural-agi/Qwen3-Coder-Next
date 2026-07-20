"""Smoke tests for Part 4 Step 7 research pipeline integration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.local_tooling.audit import AuditRecord
from qwen3_coder_next.local_tooling.commands import CommandRunResult
from qwen3_coder_next.local_tooling.contracts import CommandResult
from qwen3_coder_next.research import (
    DocumentFetcher,
    ErrorFetcher,
    EvidenceFreshness,
    EvidenceItem,
    EvidenceProvenance,
    LogFetcher,
    MalformedResearchPipelineInputError,
    ResearchBudget,
    ResearchEvidenceNormalizer,
    ResearchPacketAssembler,
    ResearchPipeline,
    ResearchPipelineResult,
    ResearchRequest,
    ResearchTaskType,
    SourcePolicy,
    SourceType,
    assemble_research_packet,
    normalize_research_evidence,
    run_research_pipeline,
    scan_local_repository,
)


class ResearchStep7SmokeTest(unittest.TestCase):
    """Verify the integrated deterministic research pipeline."""

    def _request(self) -> ResearchRequest:
        return ResearchRequest(
            request_id="req-pipeline-001",
            task_type=ResearchTaskType.INVESTIGATION,
            target_repo="Qwen-3-Coder-Next",
            query_text="pipeline integration",
            budget=ResearchBudget(source_limit=4, snippet_limit=240),
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

    def test_complete_research_pipeline_execution(self) -> None:
        """Run the full pipeline and verify stage ordering and component reuse."""

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_file = root / "research.py"
            doc_file = root / "notes.md"
            log_file = root / "app.log"
            error_file = root / "error.txt"
            repo_file.write_text("pipeline integration\nalpha\n", encoding="utf-8")
            doc_file.write_text("pipeline integration notes\n", encoding="utf-8")
            log_file.write_text("pipeline integration log\n", encoding="utf-8")
            error_file.write_text("RuntimeError: pipeline integration\n", encoding="utf-8")

            command_result = CommandResult(command="python -m test", exit_code=1, stdout="pipeline integration\n", stderr="")
            command_run = CommandRunResult(
                request_id=self._request().request_id,
                path=root / "workspace",
                allowed=True,
                result=command_result,
            )
            audit_record = AuditRecord(
                event_id="event-pipeline-001",
                sequence_number=1,
                request_id=self._request().request_id,
                timestamp=datetime.fromtimestamp(0, UTC),
                action="pipeline.run",
                subject="pipeline integration",
                status="ok",
                details={"kind": "audit"},
                metadata={"kind": "audit"},
            )
            request = self._request()
            policy = self._policy()

            pipeline = ResearchPipeline()
            result = pipeline.run(
                request,
                source_policy=policy,
                repository_root=root,
                document_refs=(doc_file,),
                log_artifacts=(audit_record, command_run, log_file),
                error_artifacts=(RuntimeError("pipeline integration"), error_file),
            )
            repeated = pipeline.run(
                request,
                source_policy=policy,
                repository_root=root,
                document_refs=(doc_file,),
                log_artifacts=(audit_record, command_run, log_file),
                error_artifacts=(RuntimeError("pipeline integration"), error_file),
            )

            self.assertIsInstance(result, ResearchPipelineResult)
            self.assertEqual(result, repeated)
            self.assertEqual(
                result.stage_order,
                (
                    "repository_scan",
                    "document_fetch",
                    "log_fetch",
                    "error_fetch",
                    "evidence_normalization",
                    "packet_assembly",
                ),
            )
            self.assertEqual(result.request, request)
            self.assertEqual(result.source_policy, policy)
            self.assertEqual(
                result.repository_scan_result,
                scan_local_repository(root, request, policy),
            )
            self.assertEqual(
                result.document_fetch_result,
                DocumentFetcher().fetch(request, policy, (doc_file,), repository_root=root),
            )
            self.assertEqual(
                result.log_fetch_result,
                LogFetcher().fetch(request, policy, (audit_record, command_run, log_file), repository_root=root),
            )
            self.assertEqual(
                result.error_fetch_result,
                ErrorFetcher().fetch(request, policy, (RuntimeError("pipeline integration"), error_file)),
            )
            self.assertEqual(
                result.evidence_normalization_result,
                normalize_research_evidence(
                    (
                        result.repository_scan_result,
                        result.document_fetch_result,
                        result.log_fetch_result,
                        result.error_fetch_result,
                    ),
                    request=request,
                    source_policy=policy,
                ),
            )
            self.assertEqual(
                result.research_packet,
                assemble_research_packet(
                    request,
                    result.evidence_normalization_result,
                    source_policy=policy,
                ),
            )
            self.assertEqual(result.research_state.current_request, request)
            self.assertEqual(result.research_state.source_policy, policy)
            self.assertEqual(result.research_state.research_packet, result.research_packet)
            self.assertGreater(len(result.research_state.revision_history), 0)
            self.assertEqual(result.source_handles[0].source_ref, ".")

    def test_deterministic_pipeline_output(self) -> None:
        """Return identical pipeline results for equivalent inputs."""

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "research.py").write_text("pipeline integration\n", encoding="utf-8")
            request = self._request()
            policy = self._policy()

            first = run_research_pipeline(
                request,
                source_policy=policy,
                repository_root=root,
            )
            second = run_research_pipeline(
                request,
                source_policy=policy,
                repository_root=root,
            )

            self.assertEqual(first, second)
            self.assertEqual(first.research_packet, second.research_packet)
            self.assertEqual(first.stage_order, second.stage_order)

    def test_malformed_input_handling(self) -> None:
        """Reject malformed pipeline inputs."""

        request = self._request()
        policy = self._policy()

        with self.assertRaises(MalformedResearchPipelineInputError):
            run_research_pipeline("bad", source_policy=policy)  # type: ignore[arg-type]
        with self.assertRaises(MalformedResearchPipelineInputError):
            ResearchPipeline().run(request, source_policy="bad")  # type: ignore[arg-type]

    def test_read_only_behavior(self) -> None:
        """Leave the repository contents unchanged during pipeline execution."""

        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repo_file = root / "research.py"
            repo_file.write_text("pipeline integration\n", encoding="utf-8")
            before = repo_file.read_text(encoding="utf-8")

            run_research_pipeline(
                self._request(),
                source_policy=self._policy(),
                repository_root=root,
                document_refs=(),
                log_artifacts=(),
                error_artifacts=(),
            )

            after = repo_file.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
