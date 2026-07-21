"""Smoke tests for Part 4 Step 9 research integration closure."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.execution import Executor
from qwen3_coder_next.logging import ApplicationLogger
from qwen3_coder_next.research import (
    MalformedResearchPipelineInputError,
    ResearchPipeline,
    ResearchRequest,
    ResearchTaskType,
    ResearchNextAction,
    SourcePolicy,
    SourceType,
    run_research_pipeline,
)
from qwen3_coder_next.runtime import Orchestrator


class ResearchStep9SmokeTest(unittest.TestCase):
    """Verify planner-to-research handoff and deterministic end-to-end replay."""

    def _settings(self, workspace_root: Path) -> AppSettings:
        return AppSettings(
            environment=EnvironmentName.TESTING,
            debug=True,
            workspace_root=workspace_root,
            artifacts_dir=workspace_root / "artifacts",
            data_dir=workspace_root / "data",
            logs_dir=workspace_root / "logs",
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

    def test_planner_research_coding_handoff(self) -> None:
        """Run planner -> research -> executor using the existing runtime boundary."""

        with TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_file = workspace_root / "research.py"
            repo_file.write_text("handoff integration\n", encoding="utf-8")

            orchestrator = Orchestrator.initialize(self._settings(workspace_root))
            try:
                planning_result = orchestrator.plan("handoff integration")
                research_request = ResearchRequest(
                    request_id=planning_result.pipeline.request.task_id,
                    task_type=ResearchTaskType.INVESTIGATION,
                    target_repo="Qwen-3-Coder-Next",
                    query_text=planning_result.pipeline.request.user_goal,
                )

                research_result = run_research_pipeline(
                    research_request,
                    source_policy=self._policy(),
                    repository_root=workspace_root,
                )
                execution_result = Executor(orchestrator).execute("handoff integration")

                self.assertGreater(len(research_result.research_packet.evidence), 0)
                self.assertEqual(research_result.research_packet.recommended_next_action, ResearchNextAction.CODE)
                self.assertTrue(execution_result.success)
                self.assertIsNotNone(orchestrator.last_planning_result)
                self.assertEqual(
                    orchestrator.last_planning_result.pipeline.request.user_goal,
                    "handoff integration",
                )
            finally:
                ApplicationLogger.shutdown("qwen3_coder_next.runtime.orchestrator")

    def test_research_pipeline_regression_and_read_only_behavior(self) -> None:
        """Verify deterministic replay, provenance preservation, and non-mutating research."""

        with TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_file = workspace_root / "research.py"
            doc_file = workspace_root / "guide.md"
            log_file = workspace_root / "app.log"
            error_file = workspace_root / "error.txt"
            repo_file.write_text("research regression\nalpha\n", encoding="utf-8")
            doc_file.write_text("research regression docs\n", encoding="utf-8")
            log_file.write_text("research regression logs\n", encoding="utf-8")
            error_file.write_text("RuntimeError: regression\n", encoding="utf-8")
            before = {
                path: path.read_text(encoding="utf-8")
                for path in (repo_file, doc_file, log_file, error_file)
            }

            request = ResearchRequest(
                request_id="req-step9-001",
                task_type=ResearchTaskType.INVESTIGATION,
                target_repo="Qwen-3-Coder-Next",
                query_text="research regression",
            )
            result = ResearchPipeline().run(
                request,
                source_policy=self._policy(),
                repository_root=workspace_root,
                document_refs=(doc_file,),
                log_artifacts=(log_file,),
                error_artifacts=(error_file,),
            )
            replay = ResearchPipeline().run(
                request,
                source_policy=self._policy(),
                repository_root=workspace_root,
                document_refs=(doc_file,),
                log_artifacts=(log_file,),
                error_artifacts=(error_file,),
            )
            after = {
                path: path.read_text(encoding="utf-8")
                for path in (repo_file, doc_file, log_file, error_file)
            }

            self.assertEqual(result, replay)
            self.assertEqual(result.research_packet, replay.research_packet)
            self.assertEqual(result.observability, replay.observability)
            self.assertTrue(result.research_packet.citations)
            self.assertTrue(all(citation for citation in result.research_packet.citations))
            self.assertEqual(result.research_packet.recommended_next_action, ResearchNextAction.CODE)
            self.assertLessEqual(len(result.research_packet.evidence), request.budget.source_limit)
            self.assertEqual(before, after)

    def test_clarification_and_unsafe_requests_do_not_fabricate_evidence(self) -> None:
        """Reject malformed pipeline inputs and keep underspecified runs in clarification mode."""

        request = ResearchRequest(
            request_id="req-step9-clarify",
            task_type=ResearchTaskType.INVESTIGATION,
            target_repo="Qwen-3-Coder-Next",
            query_text="clarification path",
        )
        clarifying = ResearchPipeline().run(
            request,
            source_policy=SourcePolicy(
                allowed_sources=(),
                preferred_sources=(),
                blocked_sources=(SourceType.REPO_FILE,),
                source_rank_weights={},
                max_evidence_items=4,
                max_snippet_chars=240,
            ),
            repository_root=None,
            document_refs=(),
            log_artifacts=(),
            error_artifacts=(),
        )

        self.assertTrue(clarifying.observability.clarification_required)
        self.assertIsNotNone(clarifying.observability.failure_record)
        self.assertEqual(
            clarifying.observability.failure_record.state_status.value,
            "needs_clarification",
        )
        self.assertEqual(
            clarifying.research_packet.recommended_next_action,
            ResearchNextAction.EXPAND_RESEARCH,
        )
        with self.assertRaises(MalformedResearchPipelineInputError):
            run_research_pipeline("unsafe", source_policy=self._policy())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main(verbosity=2)
