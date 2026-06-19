"""Unit tests for the local tooling audit logger."""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    AuditLoggerErrorCode,
    AuditLoggerRequest,
    DeterministicAuditLogger,
)


class LocalToolingAuditUnitTest(TestCase):
    """Verify append-only audit history and request tracing."""

    def test_append_creates_sequence_numbered_records(self) -> None:
        """Append an audit record with deterministic ordering."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "audit.json"
            logger = DeterministicAuditLogger(storage_path)

            result = logger.append(
                AuditLoggerRequest(
                    request_id="request-001",
                    action="artifact.registered",
                    subject="artifact-001",
                    status="ok",
                )
            )

            self.assertTrue(result.success)
            self.assertIsNotNone(result.record)
            self.assertEqual(result.record.sequence_number, 1)
            self.assertEqual(result.record.request_id, "request-001")

    def test_append_rejects_invalid_records(self) -> None:
        """Reject malformed audit requests."""

        logger = DeterministicAuditLogger()
        result = logger.append(
            AuditLoggerRequest(
                request_id="request-002",
                action="",
                subject="artifact-001",
                status="ok",
            )
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, AuditLoggerErrorCode.INVALID_RECORD)

    def test_audit_history_survives_restart(self) -> None:
        """Persist audit events to disk and reload them in a fresh logger."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "audit.json"
            logger = DeterministicAuditLogger(storage_path)
            logger.append(
                AuditLoggerRequest(
                    request_id="request-003",
                    action="artifact.registered",
                    subject="artifact-001",
                    status="ok",
                )
            )

            reloaded = DeterministicAuditLogger(storage_path)
            self.assertEqual(len(reloaded.list()), 1)
            self.assertEqual(reloaded.history("request-003")[0].subject, "artifact-001")

    def test_audit_get_raises_structured_missing_error(self) -> None:
        """Surface a structured error when an audit event is missing."""

        logger = DeterministicAuditLogger()

        with self.assertRaisesRegex(Exception, "Audit event not found for event_id"):
            logger.get("event-00000001")

    def test_audit_rejects_append_failure(self) -> None:
        """Surface append failures through the audit error model."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            blocked_parent = root / "blocked"
            blocked_parent.write_text("nope", encoding="utf-8")
            logger = DeterministicAuditLogger(blocked_parent / "audit.json")

            result = logger.append(
                AuditLoggerRequest(
                    request_id="request-004",
                    action="artifact.registered",
                    subject="artifact-001",
                    status="ok",
                )
            )

            self.assertFalse(result.success)
            self.assertEqual(result.error_code, AuditLoggerErrorCode.APPEND_FAILED)

    def test_audit_rejects_schema_mismatch_on_load(self) -> None:
        """Reject malformed persisted audit records during load."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage_path = root / "audit.json"
            with storage_path.open("w", encoding="utf-8") as handle:
                json.dump([{"event_id": "event-00000001"}], handle)

            logger = DeterministicAuditLogger(storage_path)

            with self.assertRaisesRegex(Exception, "Persisted audit record payload is missing required fields"):
                logger.list()

    def test_audit_rejects_persistence_failure_on_load(self) -> None:
        """Surface persistence failures when the audit store cannot be loaded."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage_path = root / "audit-store"
            storage_path.mkdir()
            logger = DeterministicAuditLogger(storage_path)

            with self.assertRaises(AuditLoggerError) as context:
                logger.list()

            self.assertEqual(context.exception.error_code, AuditLoggerErrorCode.PERSISTENCE_FAILED)
