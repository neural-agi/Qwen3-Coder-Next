"""Smoke tests for Part 4 Step 4 research fetchers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import tempfile
import unittest

from qwen3_coder_next.local_tooling.audit import AuditRecord
from qwen3_coder_next.local_tooling.commands import CommandRunResult
from qwen3_coder_next.local_tooling.contracts import CommandResult
from qwen3_coder_next.research import (
    DocumentFetcher,
    ErrorFetcher,
    LogFetcher,
    MalformedResearchFetchRequestError,
    ResearchRequest,
    ResearchTaskType,
    ResearchFetchResult,
    SourcePolicy,
    SourceType,
)


class ResearchStep4SmokeTest(unittest.TestCase):
    """Verify document, log, and error fetch behavior."""

    def _request(self) -> ResearchRequest:
        return ResearchRequest(
            request_id="req-fetch-001",
            task_type=ResearchTaskType.INVESTIGATION,
            target_repo="Qwen-3-Coder-Next",
            query_text="alpha trace",
        )

    def _policy(self) -> SourcePolicy:
        return SourcePolicy(
            allowed_sources=(SourceType.DOC, SourceType.LOG, SourceType.ERROR_ARTIFACT),
            preferred_sources=(SourceType.DOC, SourceType.LOG),
            blocked_sources=(),
            source_rank_weights={"doc": 1.0, "log": 0.9, "error_artifact": 0.8},
            max_evidence_items=10,
            max_snippet_chars=400,
            cache_ttl_minutes=30,
        )

    def test_document_loading_is_deterministic_and_read_only(self) -> None:
        """Load documents into evidence without mutating the filesystem."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            docs = root / "docs"
            docs.mkdir()
            first_path = docs / "b.md"
            second_path = docs / "a.md"
            first_path.write_text("beta document\nshared note\n", encoding="utf-8")
            second_path.write_text("alpha trace\nsecond line\n", encoding="utf-8")
            before = {path: path.read_text(encoding="utf-8") for path in root.rglob("*.md")}

            fetcher = DocumentFetcher()
            result = fetcher.fetch(
                self._request(),
                self._policy(),
                [Path("docs/b.md"), Path("docs/a.md"), Path("docs/b.md")],
                repository_root=root,
            )
            repeated = fetcher.fetch(
                self._request(),
                self._policy(),
                [Path("docs/b.md"), Path("docs/a.md"), Path("docs/b.md")],
                repository_root=root,
            )

            after = {path: path.read_text(encoding="utf-8") for path in root.rglob("*.md")}

            self.assertEqual(before, after)
            self.assertEqual(result, repeated)
            self.assertEqual(
                tuple(handle.source_ref for handle in result.source_handles),
                ("docs/b.md", "docs/a.md"),
            )
            self.assertEqual(
                tuple(item.source_ref for item in result.evidence_items),
                ("docs/b.md", "docs/a.md"),
            )
            self.assertTrue(all(item.provenance.tool == "document_fetcher" for item in result.evidence_items))
            self.assertEqual(ResearchFetchResult.from_dict(result.to_dict()), result)

    def test_log_fetching_uses_command_output_and_audit_records(self) -> None:
        """Convert command output, audit records, and log files into evidence."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            log_path = root / "app.log"
            log_path.write_text("alpha trace\nlog line\n", encoding="utf-8")
            before = log_path.read_text(encoding="utf-8")

            command_result = CommandResult(
                command="python -m unittest",
                exit_code=0,
                stdout="alpha trace\n",
                stderr="",
            )
            command_run = CommandRunResult(
                request_id="req-fetch-001",
                path=root / "workspace",
                allowed=True,
                result=command_result,
            )
            audit_record = AuditRecord(
                event_id="event-001",
                sequence_number=1,
                request_id="req-fetch-001",
                timestamp=datetime.fromtimestamp(0, UTC),
                action="command.run",
                subject="python -m unittest",
                status="ok",
                details={"exit_code": 0},
                metadata={"kind": "audit"},
            )

            fetcher = LogFetcher()
            result = fetcher.fetch(
                self._request(),
                self._policy(),
                [audit_record, command_run, log_path],
            )
            repeated = fetcher.fetch(
                self._request(),
                self._policy(),
                [audit_record, command_run, log_path],
            )

            after = log_path.read_text(encoding="utf-8")

            self.assertEqual(before, after)
            self.assertEqual(result, repeated)
            self.assertEqual(
                tuple(handle.source_ref for handle in result.source_handles),
                ("audit://event-001", f"command://{command_run.path.as_posix()}", log_path.as_posix()),
            )
            self.assertEqual(
                tuple(item.provenance.tool for item in result.evidence_items),
                ("log_fetcher", "log_fetcher", "log_fetcher"),
            )
            self.assertEqual(ResearchFetchResult.from_dict(result.to_dict()), result)

    def test_error_fetching_uses_stack_traces_and_error_artifacts(self) -> None:
        """Convert exceptions and error artifacts into structured evidence."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            error_path = root / "error.txt"
            error_path.write_text("ValueError: broken input\ntrace line\n", encoding="utf-8")

            try:
                raise RuntimeError("alpha trace failure")
            except RuntimeError as exc:
                captured = exc

            fetcher = ErrorFetcher()
            result = fetcher.fetch(
                self._request(),
                self._policy(),
                [captured, error_path],
            )
            repeated = fetcher.fetch(
                self._request(),
                self._policy(),
                [captured, error_path],
            )

            self.assertEqual(result, repeated)
            self.assertEqual(tuple(item.provenance.tool for item in result.evidence_items), ("error_fetcher", "error_fetcher"))
            self.assertIn("RuntimeError", result.evidence_items[0].excerpt)
            self.assertTrue(result.evidence_items[0].excerpt.startswith("Traceback"))
            self.assertEqual(result.evidence_items[1].source_ref, error_path.as_posix())
            self.assertEqual(ResearchFetchResult.from_dict(result.to_dict()), result)

    def test_malformed_input_handling_and_policy_gating(self) -> None:
        """Reject malformed iterable inputs and honor source policy boundaries."""

        request = self._request()
        doc_policy = SourcePolicy(allowed_sources=(SourceType.LOG,), max_evidence_items=1)
        log_policy = SourcePolicy(allowed_sources=(SourceType.ERROR_ARTIFACT,), max_evidence_items=1)
        error_policy = SourcePolicy(allowed_sources=(SourceType.DOC,), max_evidence_items=1)

        doc_fetcher = DocumentFetcher()
        log_fetcher = LogFetcher()
        error_fetcher = ErrorFetcher()

        with self.assertRaises(MalformedResearchFetchRequestError):
            doc_fetcher.fetch(request, self._policy(), "docs/a.md")  # type: ignore[arg-type]
        with self.assertRaises(MalformedResearchFetchRequestError):
            log_fetcher.fetch(request, self._policy(), "app.log")  # type: ignore[arg-type]
        with self.assertRaises(MalformedResearchFetchRequestError):
            error_fetcher.fetch(request, self._policy(), "error.txt")  # type: ignore[arg-type]

        self.assertEqual(doc_fetcher.fetch(request, doc_policy, [Path("docs/a.md")]).evidence_items, ())
        self.assertEqual(log_fetcher.fetch(request, log_policy, [Path("app.log")]).evidence_items, ())
        self.assertEqual(error_fetcher.fetch(request, error_policy, [Path("error.txt")]).evidence_items, ())


if __name__ == "__main__":
    unittest.main(verbosity=2)
