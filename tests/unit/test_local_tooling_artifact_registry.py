"""Unit tests for the local tooling artifact registry."""

import json
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from unittest import TestCase

from qwen3_coder_next.local_tooling import (
    ArtifactProvenance,
    ArtifactRegistryErrorCode,
    ArtifactRegistryRequest,
    DeterministicArtifactRegistry,
    RepositoryWorkspaceResolver,
    WorkspaceResolutionRequest,
)


class LocalToolingArtifactRegistryUnitTest(TestCase):
    """Verify manifests, provenance, checksums, and history semantics."""

    def _workspace(self, root: Path):
        resolver = RepositoryWorkspaceResolver(start_path=root)
        result = resolver.resolve(
            WorkspaceResolutionRequest(
                request_id="workspace-001",
                workspace_id="workspace-001",
            )
        )
        self.assertTrue(result.resolved)
        self.assertIsNotNone(result.workspace)
        return result.workspace

    def _provenance(self, request_id: str) -> ArtifactProvenance:
        return ArtifactProvenance(
            request_id=request_id,
            operation="artifact.register",
            source="unit-test",
            timestamp=datetime.now(UTC),
        )

    def test_registry_registers_manifest_with_checksum_and_provenance(self) -> None:
        """Register a manifest and preserve integrity metadata."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            workspace = self._workspace(root)
            registry = DeterministicArtifactRegistry(root / "artifacts.json")

            result = registry.register(
                ArtifactRegistryRequest(
                    request_id="artifact-001",
                    artifact_id="artifact-001",
                    name="output",
                    location=workspace.root_path / "artifacts" / "report.txt",
                    artifact_type="report",
                    content="hello\n",
                    provenance=self._provenance("artifact-001"),
                )
            )

            self.assertTrue(result.success)
            self.assertIsNotNone(result.manifest)
            self.assertEqual(result.manifest.content_checksum, sha256("hello\n".encode("utf-8")).hexdigest())
            self.assertEqual(result.manifest.provenance.request_id, "artifact-001")

    def test_duplicate_manifest_is_rejected(self) -> None:
        """Reject duplicate artifact identifiers."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            registry = DeterministicArtifactRegistry(root / "artifacts.json")
            request = ArtifactRegistryRequest(
                request_id="artifact-002",
                artifact_id="artifact-002",
                name="output",
                location=root / "artifacts" / "report.txt",
                artifact_type="report",
                content="hello\n",
                provenance=self._provenance("artifact-002"),
            )
            registry.register(request)

            duplicate = registry.register(request)
            self.assertFalse(duplicate.success)
            self.assertEqual(duplicate.error_code, ArtifactRegistryErrorCode.DUPLICATE_MANIFEST)

    def test_supersede_creates_new_history_entry(self) -> None:
        """Create a new manifest that supersedes an existing one."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            registry = DeterministicArtifactRegistry(root / "artifacts.json")
            created = registry.register(
                ArtifactRegistryRequest(
                    request_id="artifact-003",
                    artifact_id="artifact-003",
                    name="output",
                    location=root / "artifacts" / "report.txt",
                    artifact_type="report",
                    content="hello\n",
                    provenance=self._provenance("artifact-003"),
                )
            ).manifest

            superseded = registry.supersede(
                created.manifest_id,
                ArtifactRegistryRequest(
                    request_id="artifact-004",
                    artifact_id="artifact-003",
                    name="output",
                    location=root / "artifacts" / "report.txt",
                    artifact_type="report",
                    content="hello world\n",
                    provenance=self._provenance("artifact-004"),
                ),
            )

            self.assertTrue(superseded.success)
            self.assertEqual(len(registry.history("artifact-003")), 2)
            self.assertTrue(registry.get(created.manifest_id).archived)

    def test_registry_survives_restart(self) -> None:
        """Persist manifests to disk and reload them in a fresh registry."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / ".git").mkdir()
            storage_path = root / "artifacts.json"
            registry = DeterministicArtifactRegistry(storage_path)
            registry.register(
                ArtifactRegistryRequest(
                    request_id="artifact-005",
                    artifact_id="artifact-005",
                    name="output",
                    location=root / "artifacts" / "report.txt",
                    artifact_type="report",
                    content="hello\n",
                    provenance=self._provenance("artifact-005"),
                )
            )

            reloaded = DeterministicArtifactRegistry(storage_path)
            self.assertEqual(len(reloaded.list()), 1)
            self.assertEqual(reloaded.list()[0].provenance.request_id, "artifact-005")

    def test_registry_get_raises_structured_missing_error(self) -> None:
        """Surface a structured error when a manifest is missing."""

        registry = DeterministicArtifactRegistry()

        with self.assertRaisesRegex(Exception, "Manifest not found for manifest_id"):
            registry.get("missing-manifest")

    def test_registry_rejects_checksum_mismatch(self) -> None:
        """Reject a manifest when the expected checksum does not match the content."""

        registry = DeterministicArtifactRegistry()
        result = registry.register(
            ArtifactRegistryRequest(
                request_id="artifact-006",
                artifact_id="artifact-006",
                name="output",
                location=Path("/tmp/report.txt"),
                artifact_type="report",
                content="hello\n",
                provenance=self._provenance("artifact-006"),
                metadata={"expected_content_checksum": "deadbeef"},
            )
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, ArtifactRegistryErrorCode.CHECKSUM_MISMATCH)

    def test_registry_rejects_persistence_failure_on_save(self) -> None:
        """Surface persistence failures through the registry error model."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            blocked_parent = root / "blocked"
            blocked_parent.write_text("nope", encoding="utf-8")
            registry = DeterministicArtifactRegistry(blocked_parent / "artifacts.json")

            result = registry.register(
                ArtifactRegistryRequest(
                    request_id="artifact-007",
                    artifact_id="artifact-007",
                    name="output",
                    location=root / "artifacts" / "report.txt",
                    artifact_type="report",
                    content="hello\n",
                    provenance=self._provenance("artifact-007"),
                )
            )

            self.assertFalse(result.success)
            self.assertEqual(result.error_code, ArtifactRegistryErrorCode.PERSISTENCE_FAILED)

    def test_registry_rejects_invalid_manifest_on_load(self) -> None:
        """Reject malformed persisted manifests during load."""

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            storage_path = root / "artifacts.json"
            with storage_path.open("w", encoding="utf-8") as handle:
                json.dump([{"manifest_id": "manifest-001"}], handle)

            registry = DeterministicArtifactRegistry(storage_path)

            with self.assertRaisesRegex(Exception, "Persisted manifest payload is missing required fields"):
                registry.list()

    def test_manifest_identity_is_stable_across_registry_state_changes(self) -> None:
        """Generate the same manifest identity regardless of registry length."""

        registry = DeterministicArtifactRegistry()
        request = ArtifactRegistryRequest(
            request_id="artifact-008",
            artifact_id="artifact-008",
            name="output",
            location=Path("/tmp/report.txt"),
            artifact_type="report",
            content="hello\n",
            provenance=self._provenance("artifact-008"),
        )
        initial = registry._build_manifest(request)
        registry._manifests.append(
            registry._build_manifest(
                ArtifactRegistryRequest(
                    request_id="artifact-009",
                    artifact_id="artifact-009",
                    name="other",
                    location=Path("/tmp/other.txt"),
                    artifact_type="report",
                    content="goodbye\n",
                    provenance=self._provenance("artifact-009"),
                )
            )
        )
        replayed = registry._build_manifest(request)

        self.assertEqual(initial.manifest_id, replayed.manifest_id)
