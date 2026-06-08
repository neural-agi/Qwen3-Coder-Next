"""Smoke tests for the in-memory artifact manager."""

from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.artifacts import (
    ArtifactManager,
    ArtifactNotFoundError,
    DuplicateArtifactError,
)
from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.contracts import ArtifactRecord, ArtifactType
from qwen3_coder_next.logging import ApplicationLogger


class ArtifactManagerSmokeTest(unittest.TestCase):
    """Verifies core artifact manager lifecycle behavior."""

    def _build_artifact(self, artifact_id: str, path: str) -> ArtifactRecord:
        """Create an artifact record instance for testing."""

        return ArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.FILE,
            path=path,
            created_at=datetime.now(UTC),
        )

    def test_artifact_lifecycle(self) -> None:
        """Create, retrieve, update, list, and delete artifacts."""

        with TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            settings = AppSettings(
                environment=EnvironmentName.TESTING,
                debug=True,
                workspace_root=workspace_root,
                artifacts_dir=workspace_root / "artifacts",
                data_dir=workspace_root / "data",
                logs_dir=workspace_root / "logs",
            )
            ApplicationLogger.initialize(settings, logger_name="qwen3_coder_next.artifacts")

            manager = ArtifactManager()
            created_artifact = manager.create_artifact(
                self._build_artifact("artifact-001", "artifacts/file.txt")
            )

            retrieved_artifact = manager.get_artifact("artifact-001")
            self.assertEqual(retrieved_artifact, created_artifact)

            updated_artifact = ArtifactRecord(
                artifact_id="artifact-001",
                artifact_type=ArtifactType.REPORT,
                path="artifacts/report.txt",
                created_at=created_artifact.created_at,
            )
            manager.update_artifact(updated_artifact)

            artifacts = manager.list_artifacts()
            self.assertEqual(len(artifacts), 1)
            self.assertEqual(artifacts[0].artifact_type, ArtifactType.REPORT)
            self.assertEqual(artifacts[0].path, "artifacts/report.txt")

            manager.delete_artifact("artifact-001")
            self.assertEqual(manager.list_artifacts(), [])
            ApplicationLogger.shutdown("qwen3_coder_next.artifacts")

    def test_duplicate_artifact_handling(self) -> None:
        """Raise when creating a duplicate artifact."""

        manager = ArtifactManager()
        artifact = self._build_artifact("artifact-duplicate", "artifacts/file.txt")
        manager.create_artifact(artifact)

        with self.assertRaises(DuplicateArtifactError):
            manager.create_artifact(artifact)

    def test_missing_artifact_handling(self) -> None:
        """Raise when reading, updating, or deleting a missing artifact."""

        manager = ArtifactManager()
        missing_artifact = self._build_artifact("artifact-missing", "artifacts/missing.txt")

        with self.assertRaises(ArtifactNotFoundError):
            manager.get_artifact("artifact-missing")

        with self.assertRaises(ArtifactNotFoundError):
            manager.update_artifact(missing_artifact)

        with self.assertRaises(ArtifactNotFoundError):
            manager.delete_artifact("artifact-missing")


if __name__ == "__main__":
    print("Artifact manager smoke tests passed.")
    unittest.main(verbosity=2)
