import tempfile
import unittest
from pathlib import Path

from qwen3_coder_next.repo_intelligence import (
    DependencyHint,
    FileRecord,
    FolderRecord,
    ManifestStore,
    RepoSnapshot,
    SummaryRecord,
)


class RepositoryIntelligenceStep6SmokeTest(unittest.TestCase):
    def snapshot(self):
        file_record = FileRecord("src/main.py", "src/main.py", "source", "python", 4, "hash", "summary:file")
        folder = FolderRecord("src", 1, 0, ("python",), "summary:folder")
        hint = DependencyHint("src/main.py", "os", "import", 0.5, "line 1: import os")
        summary = SummaryRecord("summary:file", "src/main.py", "Source file.", "derived")
        return RepoSnapshot("repo", "/repo", "snapshot", "epoch", 1, 1, "content", (file_record,), (folder,), (hint,), (summary,))

    def test_save_load_round_trip_preserves_all_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            store = ManifestStore()
            snapshot = self.snapshot()
            self.assertEqual(store.save(snapshot, path), path)
            self.assertEqual(store.load(path), snapshot)

    def test_repeated_save_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            store = ManifestStore()
            snapshot = self.snapshot()
            store.save(snapshot, path)
            first = path.read_bytes()
            store.save(snapshot, path)
            self.assertEqual(first, path.read_bytes())

    def test_missing_corrupt_and_incompatible_manifests_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            store = ManifestStore()
            with self.assertRaises(FileNotFoundError):
                store.load(path)
            path.write_text("not-json", encoding="utf-8")
            with self.assertRaises(ValueError):
                store.load(path)
            path.write_text('{"schema_version": 99}', encoding="utf-8")
            with self.assertRaises(ValueError):
                store.load(path)

    def test_invalid_inputs_and_input_immutability(self):
        store = ManifestStore()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                store.save("bad", Path(directory) / "manifest.json")
            with self.assertRaises(ValueError):
                store.load("")
            snapshot = self.snapshot()
            store.save(snapshot, Path(directory) / "manifest.json")
            self.assertEqual(snapshot.file_count, 1)


if __name__ == "__main__":
    unittest.main()
