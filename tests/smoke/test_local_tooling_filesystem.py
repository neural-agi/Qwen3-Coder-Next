"""Smoke tests for the local tooling filesystem service boundary."""

from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    DeterministicFileSystemService,
    FileSystemOperationRequest,
    FileSystemOperationResult,
    FileSystemService,
)


class LocalToolingFilesystemSmokeTest(TestCase):
    """Verify filesystem service contracts and deterministic behavior."""

    def test_filesystem_contracts_can_be_created(self) -> None:
        """Create request and result contracts."""

        request = FileSystemOperationRequest(
            request_id="fs-001",
            path=Path("docs/example.txt"),
        )
        result = FileSystemOperationResult(
            request_id="fs-001",
            path=Path("docs/example.txt"),
            exists=False,
        )

        self.assertEqual(request.request_id, "fs-001")
        self.assertFalse(result.exists)

    def test_deterministic_filesystem_service_supports_basic_usage(self) -> None:
        """Read, write, and check existence without touching disk."""

        self.assertTrue(issubclass(DeterministicFileSystemService, FileSystemService))

        service = DeterministicFileSystemService()
        request = FileSystemOperationRequest(
            request_id="fs-002",
            path=Path("docs/example.txt"),
        )

        initial = service.exists(request)
        self.assertFalse(initial.exists)

        written = service.write(request, "hello")
        self.assertTrue(written.exists)
        self.assertEqual(written.content, "hello")

        read_back = service.read(request)
        self.assertTrue(read_back.exists)
        self.assertEqual(read_back.content, "hello")
