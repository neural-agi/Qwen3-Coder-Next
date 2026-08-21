import unittest

from qwen3_coder_next.extractors import RelationNormalizer
from qwen3_coder_next.graph import EdgeKind, NodeKind, SourceUnit
from qwen3_coder_next.parsers import ParseRequest, PythonParserAdapter


class GraphStep3Tests(unittest.TestCase):
    def _parse(self, path, text):
        unit = SourceUnit("repo", path, "python", "hash-" + path, "rev")
        return PythonParserAdapter().parse(ParseRequest(unit, "python-ast", "repo", "rev"), text)

    def test_cross_file_definitions_imports_and_calls_resolve(self):
        first = self._parse("lib.py", "def helper():\n    return 1\n")
        second = self._parse("main.py", "import helper\nhelper()\n")
        result = RelationNormalizer().normalize((second, first))
        self.assertTrue(any(node.kind == NodeKind.FUNCTION and node.qualified_name == "helper" for node in result.nodes))
        self.assertTrue(all(edge.from_node in {node.node_id for node in result.nodes} and edge.to_node in {node.node_id for node in result.nodes} for edge in result.edges))
        self.assertTrue(any(edge.kind == EdgeKind.CALLS for edge in result.edges))
        self.assertTrue(any(edge.kind == EdgeKind.DEFINES for edge in result.edges))

    def test_duplicate_order_and_ids_are_deterministic(self):
        parsed = self._parse("main.py", "def run():\n    return 1\n")
        normalizer = RelationNormalizer()
        first = normalizer.normalize((parsed, parsed))
        second = normalizer.normalize((parsed,))
        self.assertEqual(first, second)
        self.assertEqual(tuple(node.node_id for node in first.nodes), tuple(sorted(node.node_id for node in first.nodes)))

    def test_unresolved_calls_and_imports_are_explicit(self):
        parsed = self._parse("main.py", "import external_pkg\nmissing()\n")
        result = RelationNormalizer().normalize((parsed,))
        self.assertTrue(any(edge.kind == EdgeKind.IMPORTS for edge in result.edges))
        self.assertEqual(len(result.unresolved), 1)
        self.assertEqual(result.unresolved[0].qualified_name, "missing")

    def test_ambiguous_reference_is_not_guessed(self):
        first = self._parse("one.py", "def same():\n    return 1\n")
        second = self._parse("two.py", "def same():\n    return 2\n")
        caller = self._parse("main.py", "same()\n")
        result = RelationNormalizer().normalize((caller, first, second))
        self.assertEqual(len(result.unresolved), 1)
        self.assertFalse(any(edge.kind == EdgeKind.CALLS for edge in result.edges))

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            RelationNormalizer().normalize("bad")
        with self.assertRaises(ValueError):
            RelationNormalizer().normalize((object(),))


if __name__ == "__main__":
    unittest.main()
