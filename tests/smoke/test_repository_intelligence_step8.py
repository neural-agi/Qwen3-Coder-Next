import unittest
from dataclasses import FrozenInstanceError

from qwen3_coder_next.repo_intelligence import RepositoryQueryService, RepositoryQueryResult, serialize_snapshot
from qwen3_coder_next.repo_intelligence.schemas import FileRecord, FolderRecord, RepoSnapshot, SummaryRecord


class RepositoryIntelligenceStep8Tests(unittest.TestCase):
    def setUp(self):
        self.files = (
            FileRecord("src/main.py", "src/main.py", "source", "python", 10, "a"),
            FileRecord("src/theme.css", "src/theme.css", "source", "css", 10, "b"),
            FileRecord("README.md", "README.md", "documentation", "unknown", 10, "c"),
        )
        self.folders = (FolderRecord("src", 2, 0),)
        self.summaries = (
            SummaryRecord("s1", "src/main.py", "python source entry point", "derived"),
            SummaryRecord("s2", "src/theme.css", "css styling", "derived"),
        )
        self.snapshot = RepoSnapshot("repo", "/tmp/repo", "snapshot-1", "stable", 3, 1, "hash", self.files, self.folders, (), self.summaries)
        self.service = RepositoryQueryService()

    def test_prefix_type_language_and_summary_queries(self):
        result = self.service.query(self.snapshot, path_prefix="src", file_type="source", language="PYTHON")
        self.assertEqual(tuple(item.normalized_path for item in result.files), ("src/main.py",))
        self.assertEqual(tuple(item.path for item in result.folders), ("src",))
        summary_result = self.service.query(self.snapshot, summary_text="ENTRY")
        self.assertEqual(tuple(item.target_path for item in summary_result.summaries), ("src/main.py",))

    def test_empty_and_no_match_results_are_stable(self):
        empty = self.service.query(self.snapshot)
        self.assertEqual(empty, self.service.query(self.snapshot, path_prefix="/"))
        no_match = self.service.query(self.snapshot, path_prefix="missing")
        self.assertEqual(no_match, RepositoryQueryResult("snapshot-1"))

    def test_ordering_repeatability_and_read_only_behavior(self):
        before = serialize_snapshot(self.snapshot)
        first = self.service.query(self.snapshot, path_prefix="src")
        second = self.service.query(self.snapshot, path_prefix="src")
        self.assertEqual(first, second)
        self.assertEqual(serialize_snapshot(self.snapshot), before)
        with self.assertRaises(FrozenInstanceError):
            first.files += (self.files[0],)  # type: ignore[misc]

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.service.query("bad")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.service.query(self.snapshot, language=3)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
