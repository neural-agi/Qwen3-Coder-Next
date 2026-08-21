import unittest

from qwen3_coder_next.recovery import EvidenceBundle, FailureClassifier, FailureEvent, FailureCategory, Severity


class RecoveryStep4SmokeTest(unittest.TestCase):
    def _event(self, failure_type, message):
        return FailureEvent("task-4", "testing", failure_type, Severity.HIGH, message, "epoch")

    def test_each_defined_category_is_classified(self):
        classifier = FailureClassifier()
        cases = (
            ("timeout", "request timeout", FailureCategory.TRANSIENT),
            ("assertion", "assertion failed", FailureCategory.SEMANTIC),
            ("permission", "permission denied", FailureCategory.ENVIRONMENTAL),
            ("corrupted", "corrupted state", FailureCategory.UNRECOVERABLE),
        )
        for failure_type, message, expected in cases:
            report = classifier.classify(self._event(failure_type, message), EvidenceBundle(command_output=(message,)))
            self.assertEqual(report.category, expected)
            self.assertGreater(report.confidence, 0.0)
            self.assertIsNone(report.recommended_strategy)

    def test_unknown_insufficient_and_contradictory_inputs_are_explicit(self):
        classifier = FailureClassifier()
        event = self._event("mystery", "something happened")
        self.assertEqual(classifier.classify(event, EvidenceBundle()).category, FailureCategory.UNKNOWN)
        contradictory = EvidenceBundle(command_output=("timeout permission denied",))
        report = classifier.classify(event, contradictory)
        self.assertEqual(report.category, FailureCategory.UNKNOWN)
        self.assertEqual(report.confidence, 0.0)

    def test_classification_is_deterministic_and_serializable(self):
        classifier = FailureClassifier()
        event = self._event("timeout", "network timeout")
        evidence = EvidenceBundle(log_refs=("logs/a",), command_output=("network timeout",))
        first = classifier.classify(event, evidence)
        second = classifier.classify(event, evidence)
        self.assertEqual(first, second)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_malformed_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            FailureClassifier().classify("bad", EvidenceBundle())


if __name__ == "__main__":
    unittest.main()
