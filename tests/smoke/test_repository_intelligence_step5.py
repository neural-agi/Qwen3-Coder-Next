import unittest

from qwen3_coder_next.repo_intelligence import DependencyHint, FileRecord, FolderRecord, SummaryGenerator, SummaryRecord


class RepositoryIntelligenceStep5SmokeTest(unittest.TestCase):
    def test_file_summary_and_dependency_hints(self):
        record = FileRecord("src/main.py", "src/main.py", "source", "python", 10, "hash")
        hint = DependencyHint("src/main.py", "app.core", "import", 0.5, "line 1: import app.core")
        summary = SummaryGenerator().summarize_file(record, content="import app.core\ndef run(): pass", dependency_hints=(hint,))
        self.assertIn("src/main.py", summary.summary)
        self.assertIn("app.core", summary.summary)
        self.assertTrue(summary.summary_id.startswith("summary:"))

    def test_folder_summary_and_bounded_deterministic_output(self):
        generator = SummaryGenerator(max_length=80)
        folder = FolderRecord("src", 1, 0, ("python",))
        file_record = FileRecord("src/main.py", "src/main.py", "source", "python", 1, "hash")
        first = generator.summarize_folder(folder, child_files=(file_record,))
        second = generator.summarize_folder(folder, child_files=(file_record,))
        self.assertEqual(first, second)
        self.assertLessEqual(len(first.summary), 80)
        self.assertEqual(SummaryRecord.from_dict(first.to_dict()), first)

    def test_batch_generation_and_minimal_inputs(self):
        generator = SummaryGenerator()
        self.assertEqual(generator.summarize_files(()), ())
        self.assertEqual(generator.summarize_folders(()), ())
        record = FileRecord("README.md", "README.md", "documentation", "unknown", 0, "empty")
        self.assertEqual(len(generator.summarize_files((record,))), 1)

    def test_malformed_inputs_and_immutability(self):
        generator = SummaryGenerator()
        record = FileRecord("main.py", "main.py", "source", "python", 1, "hash")
        with self.assertRaises(ValueError):
            generator.summarize_file("bad")
        with self.assertRaises(ValueError):
            generator.summarize_file(record, dependency_hints=("bad",))
        with self.assertRaises(ValueError):
            generator.summarize_folder("bad")
        result = generator.summarize_file(record)
        self.assertEqual(record.file_type, "source")
        self.assertEqual(record.file_hash, "hash")
        with self.assertRaises(AttributeError):
            result.summary = "changed"


if __name__ == "__main__":
    unittest.main()
