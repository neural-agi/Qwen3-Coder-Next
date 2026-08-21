import unittest

from qwen3_coder_next.repo_intelligence import (
    ChangeEvent,
    DependencyHint,
    FileRecord,
    FolderRecord,
    RepoSnapshot,
    SummaryRecord,
    deserialize_snapshot,
    serialize_snapshot,
)


class RepositoryIntelligenceStep1SmokeTest(unittest.TestCase):
    def setUp(self):
        self.file = FileRecord("src/main.py", "src/main.py", "source", "python", 12, "hash-file", "summary:file:src/main.py", ("dep:main->util",))
        self.folder = FolderRecord("src", 1, 0, ("python",), "summary:folder:src")
        self.hint = DependencyHint("src/main.py", "src/util.py", "import", 0.8, "from util import run")
        self.summary = SummaryRecord("summary:file:src/main.py", "src/main.py", "Main module.", "epoch")
        self.change = ChangeEvent("modified", "src/main.py", "old-hash", "hash-file", "epoch")
        self.snapshot = RepoSnapshot("repo-1", "/workspace/repo", "snapshot-1", "epoch", 1, 1, "hash-snapshot", (self.file,), (self.folder,), (self.hint,), (self.summary,), (self.change,))

    def test_all_step1_contracts_are_immutable_and_serializable(self):
        for value in (self.file, self.folder, self.hint, self.summary, self.change, self.snapshot):
            self.assertIsInstance(value.to_dict(), dict)
            with self.assertRaises(AttributeError):
                value.schema_version = 2

    def test_snapshot_round_trip_is_deterministic(self):
        first = serialize_snapshot(self.snapshot)
        second = serialize_snapshot(RepoSnapshot.from_dict(self.snapshot.to_dict()))
        self.assertEqual(first, second)
        self.assertEqual(deserialize_snapshot(first), self.snapshot)

    def test_malformed_contracts_are_rejected(self):
        with self.assertRaises(ValueError):
            FileRecord("", "src/main.py", "source", "python", 1, "hash")
        with self.assertRaises(ValueError):
            DependencyHint("a", "b", "import", 2.0, "evidence")
        with self.assertRaises(ValueError):
            deserialize_snapshot("not-json")
        with self.assertRaises(ValueError):
            RepoSnapshot.from_dict({"repository_id": "repo"})

    def test_snapshot_preserves_version_and_record_counts(self):
        payload = self.snapshot.to_dict()
        payload["schema_version"] = 7
        restored = RepoSnapshot.from_dict(payload)
        self.assertEqual(restored.schema_version, 7)
        self.assertEqual(restored.file_count, 1)
        self.assertEqual(restored.folder_count, 1)


if __name__ == "__main__":
    unittest.main()
