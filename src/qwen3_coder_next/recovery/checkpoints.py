"""Injected checkpoint and rollback boundary for recovery attempts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from qwen3_coder_next.recovery.contracts import EvidenceBundle, FailureEvent


@dataclass(frozen=True, slots=True)
class CheckpointHandle:
    """Stable reference to an externally managed task/worktree snapshot."""

    checkpoint_id: str
    task_id: str
    worktree_ref: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.checkpoint_id, str) or not self.checkpoint_id.strip():
            raise ValueError("checkpoint_id must be non-empty text.")
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ValueError("task_id must be non-empty text.")
        if not isinstance(self.worktree_ref, str):
            raise ValueError("worktree_ref must be text.")

    def to_dict(self) -> dict[str, str]:
        return {"checkpoint_id": self.checkpoint_id, "task_id": self.task_id, "worktree_ref": self.worktree_ref}


@dataclass(frozen=True, slots=True)
class CheckpointResult:
    """Immutable result of checkpoint creation or rollback."""

    success: bool
    operation: str
    notes: str = ""
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.success, bool) or not isinstance(self.operation, str) or not self.operation.strip() or not isinstance(self.notes, str):
            raise ValueError("invalid checkpoint result.")
        if isinstance(self.references, (str, bytes)) or any(not isinstance(item, str) for item in self.references):
            raise ValueError("references must be text values.")
        object.__setattr__(self, "references", tuple(self.references))

    def to_dict(self) -> dict[str, object]:
        return {"success": self.success, "operation": self.operation, "notes": self.notes, "references": list(self.references)}


class CheckpointRollbackAdapter(ABC):
    """Caller-owned safe boundary for snapshot creation and restoration."""

    @abstractmethod
    def create_checkpoint(self, event: FailureEvent, evidence: EvidenceBundle) -> CheckpointHandle | CheckpointResult:
        """Create a checkpoint within an approved task/worktree boundary."""

    @abstractmethod
    def rollback(self, checkpoint: CheckpointHandle) -> CheckpointResult:
        """Restore a checkpoint without exposing arbitrary mutation to recovery."""


class CheckpointManager:
    """Validate and delegate checkpoint operations without persisting or auto-retrying."""

    def __init__(self, adapter: CheckpointRollbackAdapter) -> None:
        if not isinstance(adapter, CheckpointRollbackAdapter):
            raise ValueError("adapter must implement CheckpointRollbackAdapter.")
        self._adapter = adapter

    def create(self, event: FailureEvent, evidence: EvidenceBundle) -> CheckpointHandle | CheckpointResult:
        if not isinstance(event, FailureEvent) or not isinstance(evidence, EvidenceBundle):
            raise ValueError("event and evidence are required.")
        result = self._adapter.create_checkpoint(event, evidence)
        if not isinstance(result, (CheckpointHandle, CheckpointResult)):
            raise ValueError("adapter returned an invalid checkpoint result.")
        return result

    def rollback(self, checkpoint: CheckpointHandle) -> CheckpointResult:
        if not isinstance(checkpoint, CheckpointHandle):
            raise ValueError("checkpoint must be a CheckpointHandle.")
        result = self._adapter.rollback(checkpoint)
        if not isinstance(result, CheckpointResult) or result.operation != "rollback":
            raise ValueError("adapter returned an invalid rollback result.")
        return result
