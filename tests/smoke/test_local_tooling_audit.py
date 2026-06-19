"""Smoke tests for local tooling audit logging support."""

import tempfile
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import AuditLoggerRequest, DeterministicAuditLogger


class LocalToolingAuditSmokeTest(TestCase):
    """Verify the public audit logger boundary executes deterministically."""

    def test_deterministic_audit_logger_executes(self) -> None:
        """Append an audit event and reload it."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "audit.json"
            logger = DeterministicAuditLogger(storage_path)
            result = logger.append(
                AuditLoggerRequest(
                    request_id="audit-smoke-001",
                    action="artifact.registered",
                    subject="artifact-smoke-001",
                    status="ok",
                )
            )

            self.assertTrue(result.success)
            self.assertEqual(len(DeterministicAuditLogger(storage_path).list()), 1)

    def test_audit_logger_preserves_order_and_request_history(self) -> None:
        """Exercise append ordering, request tracing, and reload behavior."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "audit.json"
            logger = DeterministicAuditLogger(storage_path)
            first = logger.append(
                AuditLoggerRequest(
                    request_id="audit-smoke-002",
                    action="artifact.registered",
                    subject="artifact-smoke-002",
                    status="ok",
                )
            )
            second = logger.append(
                AuditLoggerRequest(
                    request_id="audit-smoke-002",
                    action="artifact.superseded",
                    subject="artifact-smoke-002",
                    status="ok",
                )
            )
            reloaded = DeterministicAuditLogger(storage_path)

            self.assertTrue(first.success)
            self.assertTrue(second.success)
            self.assertEqual([record.sequence_number for record in reloaded.list()], [1, 2])
            self.assertEqual(len(reloaded.history("audit-smoke-002")), 2)
