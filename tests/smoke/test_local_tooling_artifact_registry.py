"""Smoke tests for local tooling artifact registry support."""

import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    ArtifactProvenance,
    ArtifactRegistryRequest,
    DeterministicArtifactRegistry,
)


class LocalToolingArtifactRegistrySmokeTest(TestCase):
    """Verify the public artifact registry boundary executes deterministically."""

    def test_deterministic_artifact_registry_executes(self) -> None:
        """Register a manifest and reload it from disk."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            storage_path = root / "artifacts.json"
            registry = DeterministicArtifactRegistry(storage_path)
            content = "hello\n"
            result = registry.register(
                ArtifactRegistryRequest(
                    request_id="artifact-smoke-001",
                    artifact_id="artifact-smoke-001",
                    name="output",
                    location=root / "artifacts" / "report.txt",
                    artifact_type="report",
                    content=content,
                    provenance=ArtifactProvenance(
                        request_id="artifact-smoke-001",
                        operation="artifact.register",
                        source="smoke-test",
                        timestamp=datetime.now(UTC),
                    ),
                )
            )

            self.assertTrue(result.success)
            self.assertEqual(result.manifest.content_checksum, sha256(content.encode("utf-8")).hexdigest())
            self.assertEqual(len(DeterministicArtifactRegistry(storage_path).list()), 1)

    def test_registry_preserves_supersede_and_archive_history(self) -> None:
        """Exercise register, supersede, archive, provenance, and reload behavior."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage_path = root / "artifacts.json"
            registry = DeterministicArtifactRegistry(storage_path)
            provenance = ArtifactProvenance(
                request_id="artifact-smoke-002",
                operation="artifact.register",
                source="smoke-test",
                timestamp=datetime.now(UTC),
            )
            created = registry.register(
                ArtifactRegistryRequest(
                    request_id="artifact-smoke-002",
                    artifact_id="artifact-smoke-002",
                    name="output",
                    location=root / "artifacts" / "report.txt",
                    artifact_type="report",
                    content="hello\n",
                    provenance=provenance,
                )
            )

            superseded = registry.supersede(
                created.manifest.manifest_id,
                ArtifactRegistryRequest(
                    request_id="artifact-smoke-003",
                    artifact_id="artifact-smoke-002",
                    name="output",
                    location=root / "artifacts" / "report.txt",
                    artifact_type="report",
                    content="hello world\n",
                    provenance=ArtifactProvenance(
                        request_id="artifact-smoke-003",
                        operation="artifact.supersede",
                        source="smoke-test",
                        timestamp=datetime.now(UTC),
                    ),
                ),
            )
            archived = registry.archive(created.manifest.manifest_id, "artifact-smoke-004")
            reloaded = DeterministicArtifactRegistry(storage_path)

            self.assertTrue(created.success)
            self.assertTrue(superseded.success)
            self.assertTrue(archived.success)
            self.assertEqual(reloaded.history("artifact-smoke-002")[0].provenance.request_id, "artifact-smoke-002")
            self.assertTrue(reloaded.get(created.manifest.manifest_id).archived)
