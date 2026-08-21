import unittest

from qwen3_coder_next.repo_intelligence import FileClassifier, FileRecord


class RepositoryIntelligenceStep3SmokeTest(unittest.TestCase):
    def setUp(self):
        self.classifier = FileClassifier()

    def record(self, path):
        return FileRecord(path, path, "unknown", "unknown", 1, "hash")

    def test_representative_categories_and_languages(self):
        cases = {
            "src/main.py": ("source", "python"),
            "README.MD": ("documentation", "unknown"),
            "config/settings.yaml": ("data", "unknown"),
            "pyproject.toml": ("configuration", "unknown"),
            "tests/test_main.py": ("test", "python"),
            "dist/bundle.min.js": ("generated", "javascript"),
            "Makefile": ("build", "unknown"),
            "unknown.xyz": ("unknown", "unknown"),
        }
        for path, expected in cases.items():
            result = self.classifier.classify(self.record(path))
            self.assertEqual((result.file_type, result.language), expected, path)

    def test_precedence_and_case_normalization_are_deterministic(self):
        generated_test = self.classifier.classify(self.record("tests/generated/output.min.js"))
        self.assertEqual(generated_test.file_type, "generated")
        first = self.classifier.classify_many((self.record("B.PY"), self.record("a.md")))
        second = self.classifier.classify_many((self.record("B.PY"), self.record("a.md")))
        self.assertEqual(first, second)
        self.assertEqual([item.normalized_path for item in first], ["B.PY", "a.md"])
        self.assertEqual(first[0].language, "python")

    def test_classification_preserves_scanner_metadata_and_does_not_mutate(self):
        original = self.record("src/main.py")
        classified = self.classifier.classify(original)
        self.assertEqual(original.file_type, "unknown")
        self.assertEqual(classified.file_hash, original.file_hash)
        self.assertEqual(classified.size_bytes, original.size_bytes)
        self.assertEqual(classified.normalized_path, original.normalized_path)

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.classifier.classify("src/main.py")
        with self.assertRaises(ValueError):
            self.classifier.classify_many("src/main.py")


if __name__ == "__main__":
    unittest.main()
