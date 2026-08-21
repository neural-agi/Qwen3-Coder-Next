"""Failure recovery contracts and normalized failure ingress."""

from qwen3_coder_next.recovery.contracts import (
    DiagnosisReport,
    EvidenceBundle,
    FailureCategory,
    FailureEvent,
    RecoveryOutcome,
    RecoveryPlan,
    RecoveryRecord,
    RecoveryStrategy,
    Severity,
)
from qwen3_coder_next.recovery.ingress import FailureIngress
from qwen3_coder_next.recovery.evidence import EvidenceCapture
from qwen3_coder_next.recovery.classifier import FailureClassifier
from qwen3_coder_next.recovery.strategy import StrategyRegistry, StrategyRule
from qwen3_coder_next.recovery.executor import RecoveryAttemptResult, RecoveryExecutionAdapter, RecoveryExecutor
from qwen3_coder_next.recovery.checkpoints import CheckpointHandle, CheckpointManager, CheckpointResult, CheckpointRollbackAdapter
from qwen3_coder_next.recovery.ledger import InMemoryRecoveryLedger, InMemoryRecoveryMetrics, RecoveryLedger, RecoveryMetrics

__all__ = [
    "DiagnosisReport",
    "EvidenceBundle",
    "FailureCategory",
    "FailureEvent",
    "FailureIngress",
    "EvidenceCapture",
    "FailureClassifier",
    "StrategyRegistry",
    "StrategyRule",
    "RecoveryAttemptResult",
    "RecoveryExecutionAdapter",
    "RecoveryExecutor",
    "CheckpointHandle",
    "CheckpointManager",
    "CheckpointResult",
    "CheckpointRollbackAdapter",
    "RecoveryLedger",
    "InMemoryRecoveryLedger",
    "RecoveryMetrics",
    "InMemoryRecoveryMetrics",
    "RecoveryOutcome",
    "RecoveryPlan",
    "RecoveryRecord",
    "RecoveryStrategy",
    "Severity",
]
