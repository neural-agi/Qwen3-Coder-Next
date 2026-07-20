"""Smoke tests for Part 4 Step 3 local repository scanning."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from qwen3_coder_next.research import (
    LocalRepositoryScanner,
    MalformedRepositoryScanRequestError,
    ResearchBudget,
    ResearchRequest,
    ResearchTaskType,
    RepositoryScanResult,
    SourcePolicy,
    SourceType,
    scan_local_repository,
)


class ResearchStep3SmokeTest(unittest.TestCase):
    """Verify deterministic local repository scanning behavior."""

    def test_repository_walk_filtering_and_snippet_extraction(self) -> None:
        """Walk a repository and extract focused snippets for matching paths."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "docs").mkdir()
            (root / "src").mkdir()
            (root / "docs" / "architecture.md").write_text(
                "Architecture overview\nScanner boundary\nRepository evidence\n",
                encoding="utf-8",
            )
            (root / "src" / "module_a.py").write_text(
                "def alpha():\n    return 'needle'\n",
                encoding="utf-8",
            )
            (root / "src" / "module_b.py").write_text(
                "def beta():\n    return 'other'\n",
                encoding="utf-8",
            )
            (root / "README.md").write_text("Repository scanner reference\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "ignored.txt").write_text("should not be scanned\n", encoding="utf-8")

            request = ResearchRequest(
                request_id="req-scan-001",
                task_type=ResearchTaskType.INVESTIGATION,
                target_repo="Qwen-3-Coder-Next",
                query_text="needle",
                constraints=("docs/architecture.md",),
                hints=("src/module_a.py",),
                budget=ResearchBudget(source_limit=5, snippet_limit=120),
            )
            policy = SourcePolicy(
                allowed_sources=(SourceType.REPO_FILE,),
                preferred_sources=(SourceType.REPO_FILE,),
                max_evidence_items=5,
                max_snippet_chars=120,
            )

            result = scan_local_repository(root, request, policy)

            self.assertIsInstance(result, RepositoryScanResult)
            self.assertEqual(
                result.candidate_paths,
                (
                    "README.md",
                    "docs/architecture.md",
                    "src/module_a.py",
                    "src/module_b.py",
                ),
            )
            self.assertEqual(result.selected_paths, ("src/module_a.py", "docs/architecture.md"))
            self.assertEqual(result.repository_metadata["candidate_file_count"], 4)
            self.assertEqual(result.repository_metadata["selected_file_count"], 2)
            self.assertEqual(result.source_handles[0].source_type, SourceType.REPO_FOLDER)
            self.assertEqual(
                tuple(handle.source_ref for handle in result.source_handles[1:]),
                result.selected_paths,
            )
            self.assertIn("needle", result.evidence_items[0].excerpt)
            self.assertIn("Scanner boundary", result.evidence_items[1].excerpt)
            self.assertEqual(RepositoryScanResult.from_dict(result.to_dict()), result)

    def test_file_sampling_is_deterministic(self) -> None:
        """Select a stable subset when the scanner is limited to one file."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "src").mkdir()
            (root / "src" / "a.md").write_text("needle line one\nneedle line two\n", encoding="utf-8")
            (root / "src" / "b.md").write_text("needle line three\nneedle line four\n", encoding="utf-8")

            request = ResearchRequest(
                request_id="req-scan-002",
                task_type=ResearchTaskType.BUG,
                target_repo="Qwen-3-Coder-Next",
                query_text="needle",
                budget=ResearchBudget(source_limit=1, snippet_limit=60),
            )
            policy = SourcePolicy(
                allowed_sources=(SourceType.REPO_FILE,),
                preferred_sources=(SourceType.REPO_FILE,),
                max_evidence_items=1,
                max_snippet_chars=60,
            )
            scanner = LocalRepositoryScanner(max_file_count=1, max_snippet_chars=60)

            first = scanner.scan(root, request, policy)
            second = scanner.scan(root, request, policy)

            self.assertEqual(first, second)
            self.assertEqual(first.selected_paths, ("src/a.md",))
            self.assertEqual(len(first.evidence_items), 1)
            self.assertIn("needle line one", first.evidence_items[0].excerpt)
            self.assertEqual(RepositoryScanResult.from_dict(first.to_dict()), first)

    def test_read_only_behavior_and_malformed_inputs(self) -> None:
        """Leave the repository unchanged and reject malformed requests."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "notes.md").write_text("read only scan\n", encoding="utf-8")
            before_listing = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            before_contents = {path: path.read_text(encoding="utf-8") for path in root.rglob("*.md")}

            request = ResearchRequest(
                request_id="req-scan-003",
                task_type=ResearchTaskType.INVESTIGATION,
                target_repo="Qwen-3-Coder-Next",
                query_text="read only",
                budget=ResearchBudget(source_limit=1, snippet_limit=40),
            )
            policy = SourcePolicy(allowed_sources=(SourceType.REPO_FILE,), max_evidence_items=1)
            scanner = LocalRepositoryScanner()

            result = scanner.scan(root, request, policy)

            after_listing = sorted(str(path.relative_to(root)) for path in root.rglob("*"))
            after_contents = {path: path.read_text(encoding="utf-8") for path in root.rglob("*.md")}

            self.assertEqual(before_listing, after_listing)
            self.assertEqual(before_contents, after_contents)
            self.assertEqual(result.repository_metadata["warning_count"], 0)

            with self.assertRaises(MalformedRepositoryScanRequestError):
                scanner.scan(root / "missing", request, policy)

            with self.assertRaises(MalformedRepositoryScanRequestError):
                scanner.scan(root, "bad-request", policy)  # type: ignore[arg-type]

    def test_oversized_files_are_skipped_with_metadata(self) -> None:
        """Skip files above the size threshold and record the skip in metadata."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            oversized = root / "large.md"
            oversized.write_bytes(b"a" * (5 * 1024 * 1024 + 1))
            (root / "small.md").write_text("needle\n", encoding="utf-8")

            request = ResearchRequest(
                request_id="req-scan-004",
                task_type=ResearchTaskType.INVESTIGATION,
                target_repo="Qwen-3-Coder-Next",
                query_text="needle",
                budget=ResearchBudget(source_limit=5, snippet_limit=40),
            )
            policy = SourcePolicy(allowed_sources=(SourceType.REPO_FILE,), max_evidence_items=5)

            result = scan_local_repository(root, request, policy)

            self.assertEqual(result.repository_metadata["oversized_file_count"], 1)
            self.assertEqual(result.repository_metadata["ignored_file_count"], 0)
            self.assertEqual(result.selected_paths, ("small.md",))
            self.assertTrue(any("oversized" in warning.lower() for warning in result.warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
