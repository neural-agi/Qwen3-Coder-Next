import tempfile
import unittest
from pathlib import Path

from qwen3_coder_next.repo_intelligence import DependencyHintExtractor, FileClassifier, FileRecord


class RepositoryIntelligenceStep4SmokeTest(unittest.TestCase):
    def test_supported_import_forms_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("import os\nfrom app.core import run\n", encoding="utf-8")
            record = FileClassifier().classify(FileRecord("main.py", "main.py", "unknown", "python", 1, "hash"))
            hints = DependencyHintExtractor().extract(record, root)
            self.assertEqual([hint.target_path for hint in hints], ["app.core", "os"])
            self.assertTrue(all(hint.evidence and hint.confidence == 0.5 for hint in hints))

    def test_multiple_languages_and_deterministic_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.js").write_text("require('./z');\nimport x from './a';\n", encoding="utf-8")
            (root / "main.h").write_text('#include "local.h"\n#include <stdio.h>\n', encoding="utf-8")
            classifier = FileClassifier()
            records = tuple(classifier.classify(FileRecord(name, name, "unknown", "unknown", 1, "hash")) for name in ("main.js", "main.h"))
            extractor = DependencyHintExtractor()
            first = extractor.extract_many(records, root)
            second = extractor.extract_many(records, root)
            self.assertEqual(first, second)
            self.assertEqual([hint.target_path for hint in first], ["local.h", "stdio.h", "./a", "./z"])

    def test_unresolved_and_unsupported_inputs_are_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "unknown.xyz").write_text("import no_parser", encoding="utf-8")
            record = FileRecord("unknown.xyz", "unknown.xyz", "unknown", "unknown", 1, "hash")
            self.assertEqual(DependencyHintExtractor().extract(record, root), ())
            with self.assertRaises(ValueError):
                DependencyHintExtractor().extract("bad", root)
            with self.assertRaises(ValueError):
                DependencyHintExtractor().extract(record, root / "missing")

    def test_metadata_and_input_records_are_not_mutated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("import os\n", encoding="utf-8")
            record = FileRecord("main.py", "main.py", "source", "python", 9, "stable", "summary", ("dep:existing",))
            DependencyHintExtractor().extract(record, root)
            self.assertEqual(record.to_dict()["hash"], "stable")
            self.assertEqual(record.dependency_refs, ("dep:existing",))


if __name__ == "__main__":
    unittest.main()
