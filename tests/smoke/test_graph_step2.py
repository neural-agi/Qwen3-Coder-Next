import unittest
from dataclasses import FrozenInstanceError

from qwen3_coder_next.graph import SourceUnit
from qwen3_coder_next.parsers import FactKind, ParseRequest, PythonParserAdapter, UnsupportedLanguageError


class GraphStep2Tests(unittest.TestCase):
    def setUp(self):
        self.source = SourceUnit("repo", "src/main.py", "python", "hash", "rev-1")
        self.request = ParseRequest(self.source, "python-ast", "repository", "rev-1")
        self.adapter = PythonParserAdapter()

    def test_python_adapter_extracts_deterministic_facts(self):
        text = "import os\nclass Service:\n    def run(self):\n        return helper()\nvalue = 1\n"
        first = self.adapter.parse(self.request, text)
        second = self.adapter.parse(self.request, text)
        self.assertEqual(first, second)
        kinds = {fact.kind for fact in first.facts}
        self.assertTrue({FactKind.MODULE, FactKind.IMPORT, FactKind.CLASS, FactKind.FUNCTION, FactKind.CALL, FactKind.VARIABLE} <= kinds)
        qualified_names = {fact.qualified_name for fact in first.facts}
        self.assertIn("Service.run", qualified_names)
        self.assertIn("helper", qualified_names)
        self.assertEqual(first.facts, tuple(sorted(first.facts, key=lambda item: (item.line, item.column, item.kind.value, item.qualified_name))))
        self.assertEqual(first.facts[0].provenance, ("src/main.py:1",))

    def test_syntax_failure_is_explicit_and_non_mutating(self):
        result = self.adapter.parse(self.request, "def broken(:\n")
        self.assertEqual(result.facts, ())
        self.assertTrue(result.warnings)
        with self.assertRaises(FrozenInstanceError):
            result.facts += ()  # type: ignore[misc]

    def test_unsupported_language_is_rejected(self):
        request = ParseRequest(SourceUnit("repo", "main.rs", "rust", "hash", "rev-1"), "rust", "repository", "rev-1")
        with self.assertRaises(UnsupportedLanguageError):
            self.adapter.parse(request, "fn main() {}")

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            ParseRequest("bad", "python", "scope", "rev")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            self.adapter.parse(self.request, 3)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
