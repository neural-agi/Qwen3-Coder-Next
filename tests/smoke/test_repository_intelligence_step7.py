import tempfile
import unittest
from pathlib import Path

from qwen3_coder_next.repo_intelligence import (
    DependencyHintExtractor,
    FileClassifier,
    IncrementalRefresher,
    RepositoryScanner,
    SummaryGenerator,
    serialize_snapshot,
)
from qwen3_coder_next.repo_intelligence.schemas import RepoSnapshot


class RepositoryIntelligenceStep7Tests(unittest.TestCase):
    def _snapshot(self, root: Path) -> RepoSnapshot:
        scan = RepositoryScanner().scan(root)
        files = FileClassifier().classify_many(scan.files)
        hints = DependencyHintExtractor().extract_many(files, root)
        summaries = SummaryGenerator().summarize_files(
            files,
            contents={item.normalized_path: (root / item.path).read_text(encoding="utf-8") for item in files},
            dependency_hints=hints,
        )
        return RepoSnapshot("repo", root.resolve().as_posix(), "initial", "stable", len(files), len(scan.folders), "initial", files, scan.folders, hints, summaries)

    def test_refresh_reuses_unchanged_records_and_journals_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("import os\n", encoding="utf-8")
            (root / "b.txt").write_text("stable\n", encoding="utf-8")
            initial = self._snapshot(root)
            unchanged = next(item for item in initial.files if item.normalized_path == "b.txt")
            (root / "a.py").write_text("import sys\n", encoding="utf-8")
            (root / "b.txt").unlink()
            (root / "c.py").write_text("import json\n", encoding="utf-8")

            refreshed = IncrementalRefresher().refresh(initial, root)

            self.assertEqual(tuple(item.normalized_path for item in refreshed.files), ("a.py", "c.py"))
            self.assertNotIn("b.txt", {item.normalized_path for item in refreshed.files})
            self.assertEqual([event.change_type for event in refreshed.changes], ["modified", "deleted", "added"])
            self.assertEqual(next(item for item in refreshed.files if item.normalized_path == "a.py").file_type, "source")
            self.assertEqual(unchanged.file_hash, next(item for item in initial.files if item.normalized_path == "b.txt").file_hash)

    def test_refresh_is_deterministic_and_does_not_mutate_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("import os\n", encoding="utf-8")
            initial = self._snapshot(root)
            before = serialize_snapshot(initial)
            first = IncrementalRefresher().refresh(initial, root)
            second = IncrementalRefresher().refresh(initial, root)
            self.assertEqual(serialize_snapshot(first), serialize_snapshot(second))
            self.assertEqual(serialize_snapshot(initial), before)
            self.assertEqual(first.files, initial.files)
            self.assertEqual(first.changes, ())

    def test_invalid_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                IncrementalRefresher().refresh("bad", root)  # type: ignore[arg-type]
            with self.assertRaises(ValueError):
                IncrementalRefresher().refresh(self._snapshot(root), root / "missing")


if __name__ == "__main__":
    unittest.main()
