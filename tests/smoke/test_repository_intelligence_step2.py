import tempfile
import unittest
from pathlib import Path

from qwen3_coder_next.repo_intelligence import RepositoryScanner


class RepositoryIntelligenceStep2SmokeTest(unittest.TestCase):
    def test_scan_is_deterministic_and_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src" / "nested").mkdir(parents=True)
            (root / "src" / "main.py").write_text("print('ok')", encoding="utf-8")
            (root / "src" / "nested" / "data.txt").write_text("data", encoding="utf-8")
            scanner = RepositoryScanner()
            first = scanner.scan(root)
            second = scanner.scan(root)
            self.assertEqual(first, second)
            self.assertEqual([item.normalized_path for item in first.files], ["src/main.py", "src/nested/data.txt"])
            self.assertEqual([item.path for item in first.folders], ["src", "src/nested"])
            self.assertEqual(first.files[0].file_type, "unknown")
            self.assertEqual(len(first.files[0].file_hash), 64)

    def test_default_and_custom_ignore_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("ignored", encoding="utf-8")
            (root / "generated.tmp").write_text("ignored", encoding="utf-8")
            (root / "keep.py").write_text("kept", encoding="utf-8")
            result = RepositoryScanner(ignored_directories=(".git", "*.tmp")).scan(root)
            self.assertEqual([item.normalized_path for item in result.files], ["keep.py"])
            self.assertEqual(result.ignored_paths, (".git", "generated.tmp"))

    def test_empty_directories_and_invalid_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "empty").mkdir()
            result = RepositoryScanner().scan(root)
            self.assertEqual(result.files, ())
            self.assertEqual(result.folders[0].path, "empty")
            with self.assertRaises(ValueError):
                RepositoryScanner().scan(root / "missing")

    def test_symlinks_are_ignored_without_following_them_when_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real.txt").write_text("real", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(root / "real.txt")
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            result = RepositoryScanner().scan(root)
            self.assertEqual([item.normalized_path for item in result.files], ["real.txt"])
            self.assertEqual(result.ignored_paths, ("link.txt",))


if __name__ == "__main__":
    unittest.main()
