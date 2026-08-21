import unittest

from qwen3_coder_next.recovery import EvidenceCapture, FailureEvent, Severity


class RecoveryStep3SmokeTest(unittest.TestCase):
    def _event(self):
        return FailureEvent("task-3", "testing", "timeout", Severity.HIGH, "test timeout", "epoch", worktree_ref="wt-1")

    def test_captures_all_supported_sources_without_mutation(self):
        event = self._event()
        bundle = EvidenceCapture().capture(
            event,
            recent_actions=("run tests",),
            log_refs=("logs/run.txt#L1",),
            command_output=("timed out",),
            memory_refs=("memory-1",),
            file_anchors=("src/app.py:10",),
            agent_status="blocked",
        )
        self.assertEqual(bundle.worktree_ref, "wt-1")
        self.assertEqual(bundle.agent_status, "blocked")
        self.assertEqual(bundle.to_dict()["log_refs"], ["logs/run.txt#L1"])
        self.assertEqual(event.worktree_ref, "wt-1")

    def test_output_is_deterministic_and_immutable(self):
        capture = EvidenceCapture()
        first = capture.capture(self._event(), recent_actions=("a", "b"), log_refs=("l",))
        second = capture.capture(self._event(), recent_actions=("a", "b"), log_refs=("l",))
        self.assertEqual(first, second)
        with self.assertRaises(AttributeError):
            first.agent_status = "changed"

    def test_empty_capture_and_malformed_inputs(self):
        empty = EvidenceCapture().capture(self._event())
        self.assertEqual(empty.recent_actions, ())
        with self.assertRaises(ValueError):
            EvidenceCapture().capture("bad")
        with self.assertRaises(ValueError):
            EvidenceCapture().capture(self._event(), log_refs="not-a-list")
        with self.assertRaises(ValueError):
            EvidenceCapture().capture(self._event(), worktree_ref="other")


if __name__ == "__main__":
    unittest.main()
