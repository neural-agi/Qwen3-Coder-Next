import unittest

from qwen3_coder_next.recovery import FailureCategory, FailureEvent, FailureIngress, Severity


class RecoveryStep1And2SmokeTest(unittest.TestCase):
    def test_contract_is_immutable_and_serializable(self):
        event = FailureEvent("task-1", "tool", "timeout", Severity.HIGH, "timed out", "epoch", retry_count=1)
        self.assertEqual(event.to_dict()["severity"], "high")
        with self.assertRaises(AttributeError):
            event.message = "changed"
        self.assertEqual(FailureCategory.TRANSIENT.value, "transient")

    def test_exception_and_envelope_normalization(self):
        ingress = FailureIngress()
        exception_event = ingress.normalize(TimeoutError("slow"), task_id="task-1", source_agent="tool", timestamp="epoch")
        envelope_event = ingress.normalize({"failure_type": "permission", "message": "denied", "severity": "critical", "retry_count": 2}, task_id="task-1", source_agent="agent", timestamp="epoch")
        self.assertEqual(exception_event.failure_type, "timeouterror")
        self.assertEqual(envelope_event.retry_count, 2)

    def test_malformed_ingress_is_rejected(self):
        with self.assertRaises(ValueError):
            FailureIngress().normalize({}, task_id="task-1", source_agent="tool", timestamp="epoch")
        with self.assertRaises(ValueError):
            FailureIngress().normalize(Exception("bad"), task_id="task-1", source_agent="unknown", timestamp="epoch")


if __name__ == "__main__":
    unittest.main()
