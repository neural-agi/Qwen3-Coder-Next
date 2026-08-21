import tempfile
import unittest
from pathlib import Path

from qwen3_coder_next.repo_intelligence import (
    DependencyHintExtractor,
    FileClassifier,
    IncrementalRefresher,
    ManifestStore,
    RepositoryQueryService,
    RepositoryScanner,
    SummaryGenerator,
    serialize_snapshot,
)
from qwen3_coder_next.repo_intelligence.schemas import RepoSnapshot


class RepositoryIntelligenceStep9Tests(unittest.TestCase):
    def _build_snapshot(self, root: Path) -> RepoSnapshot:
        scan = RepositoryScanner().scan(root)
        files = FileClassifier().classify_many(scan.files)
        hints = DependencyHintExtractor().extract_many(files, root)
        contents = {
            item.normalized_path: (root / item.path).read_text(encoding="utf-8")
            for item in files
            if item.language != "unknown"
        }
        generator = SummaryGenerator()
        summaries = list(generator.summarize_files(files, contents=contents, dependency_hints=hints))
        summaries.extend(generator.summarize_folders(scan.folders, files=files, folders=scan.folders))
        return RepoSnapshot(
            "fixture-repository",
            root.resolve().as_posix(),
            "fixture-initial",
            "fixture-time",
            len(files),
            len(scan.folders),
            "fixture-content",
            files,
            scan.folders,
            hints,
            tuple(summaries),
        )

    def test_fixture_pipeline_persists_and_queries_without_rescanning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "docs").mkdir()
            (root / "src" / "main.py").write_text("import json\nprint('ok')\n", encoding="utf-8")
            (root / "src" / "web.ts").write_text("import x from './x'\n", encoding="utf-8")
            (root / "docs" / "README.md").write_text("Repository guide\n", encoding="utf-8")
            (root / "vendor").mkdir()
            (root / "vendor" / "ignored.py").write_text("ignored = True\n", encoding="utf-8")

            snapshot = self._build_snapshot(root)
            manifest = root / ".state" / "manifest.json"
            store = ManifestStore()
            store.save(snapshot, manifest)
            reloaded = store.load(manifest)
            query = RepositoryQueryService()
            result = query.query(reloaded, path_prefix="src")

            self.assertEqual(serialize_snapshot(reloaded), serialize_snapshot(snapshot))
            self.assertEqual(tuple(item.normalized_path for item in result.files), ("src/main.py", "src/web.ts"))
            self.assertEqual(tuple(item.path for item in result.folders), ("src",))
            self.assertTrue(any(item.target_path == "src/main.py" for item in result.summaries))
            self.assertTrue(any(item.target_path == "src" for item in result.summaries))
            self.assertNotIn("vendor/ignored.py", {item.normalized_path for item in reloaded.files})
            self.assertEqual(result, query.query(reloaded, path_prefix="src"))

    def test_incremental_fixture_refresh_reuses_unchanged_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("import json\n", encoding="utf-8")
            (root / "stable.txt").write_text("unchanged\n", encoding="utf-8")
            initial = self._build_snapshot(root)
            stable = next(item for item in initial.files if item.normalized_path == "stable.txt")
            (root / "src" / "main.py").write_text("import os\n", encoding="utf-8")
            (root / "stable.txt").write_text("unchanged\n", encoding="utf-8")
            (root / "new.py").write_text("import sys\n", encoding="utf-8")

            first = IncrementalRefresher().refresh(initial, root)
            second = IncrementalRefresher().refresh(initial, root)

            self.assertEqual(serialize_snapshot(first), serialize_snapshot(second))
            self.assertEqual(next(item for item in first.files if item.normalized_path == "stable.txt"), stable)
            self.assertEqual([event.change_type for event in first.changes], ["added", "modified"])
            self.assertEqual(
                {event.path for event in first.changes},
                {"src/main.py", "new.py"},
            )

            (root / "src" / "main.py").unlink()
            deleted = IncrementalRefresher().refresh(first, root)
            self.assertEqual([event.change_type for event in deleted.changes], ["deleted"])
            self.assertEqual(deleted.changes[0].path, "src/main.py")

    def test_minimal_fixture_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = self._build_snapshot(root)
            refreshed = IncrementalRefresher().refresh(initial, root)
            self.assertEqual(refreshed.files, ())
            self.assertEqual(refreshed.folders, ())
            self.assertEqual(refreshed.changes, ())
            self.assertEqual(serialize_snapshot(refreshed), serialize_snapshot(IncrementalRefresher().refresh(initial, root)))


if __name__ == "__main__":
    unittest.main()
