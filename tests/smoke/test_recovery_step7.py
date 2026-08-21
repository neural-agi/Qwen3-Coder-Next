import unittest

from qwen3_coder_next.recovery import (
    CheckpointHandle,
    CheckpointManager,
    CheckpointResult,
    CheckpointRollbackAdapter,
    EvidenceBundle,
    FailureEvent,
    Severity,
)


class Adapter(CheckpointRollbackAdapter):
    def __init__(self, rollback_result):
        self.rollback_result = rollback_result
        self.created = []
        self.restored = []

    def create_checkpoint(self, event, evidence):
        handle = CheckpointHandle("cp-1", event.task_id, evidence.worktree_ref)
        self.created.append(handle)
        return handle

    def rollback(self, checkpoint):
        self.restored.append(checkpoint)
        return self.rollback_result


class RecoveryStep7SmokeTest(unittest.TestCase):
    def setUp(self):
        self.event = FailureEvent("task-7", "testing", "timeout", Severity.HIGH, "timeout", "epoch", worktree_ref="wt-7")
        self.evidence = EvidenceBundle(worktree_ref="wt-7", log_refs=("logs/failure",))

    def test_checkpoint_creation_and_successful_rollback(self):
        adapter = Adapter(CheckpointResult(True, "rollback", "restored"))
        manager = CheckpointManager(adapter)
        handle = manager.create(self.event, self.evidence)
        self.assertIsInstance(handle, CheckpointHandle)
        self.assertEqual(handle.to_dict()["worktree_ref"], "wt-7")
        result = manager.rollback(handle)
        self.assertTrue(result.success)
        self.assertEqual(len(adapter.restored), 1)

    def test_rollback_failure_is_reported_without_success(self):
        manager = CheckpointManager(Adapter(CheckpointResult(False, "rollback", "restore failed")))
        handle = manager.create(self.event, self.evidence)
        result = manager.rollback(handle)
        self.assertFalse(result.success)
        self.assertEqual(result.notes, "restore failed")

    def test_repeated_rollback_is_explicit_and_deterministic(self):
        adapter = Adapter(CheckpointResult(True, "rollback", "already restored"))
        manager = CheckpointManager(adapter)
        handle = manager.create(self.event, self.evidence)
        first = manager.rollback(handle)
        second = manager.rollback(handle)
        self.assertEqual(first, second)
        self.assertEqual(len(adapter.restored), 2)

    def test_malformed_adapter_and_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            CheckpointManager(object())
        manager = CheckpointManager(Adapter(CheckpointResult(True, "rollback")))
        with self.assertRaises(ValueError):
            manager.create("bad", self.evidence)
        with self.assertRaises(ValueError):
            manager.rollback("bad")

    def test_contracts_are_immutable_and_no_persistence_is_present(self):
        result = CheckpointResult(True, "rollback")
        with self.assertRaises(AttributeError):
            result.success = False
        self.assertFalse(hasattr(CheckpointManager, "save"))
        self.assertFalse(hasattr(CheckpointManager, "load"))


if __name__ == "__main__":
    unittest.main()
