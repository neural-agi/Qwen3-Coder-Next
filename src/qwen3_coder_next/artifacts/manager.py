"""Stable API layer for artifact management."""

from qwen3_coder_next.artifacts.store import ArtifactStore
from qwen3_coder_next.contracts import ArtifactRecord
from qwen3_coder_next.logging import get_logger


class ArtifactManager:
    """Manage artifact operations through a store and logger."""

    def __init__(self, store: ArtifactStore | None = None) -> None:
        """Initialize the artifact manager with an in-memory store."""

        self._store = store or ArtifactStore()
        self._logger = get_logger("qwen3_coder_next.artifacts")

    def create_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        """Create and log a new artifact."""

        self._logger.info("Creating artifact for artifact_id=%s", artifact.artifact_id)
        return self._store.create_artifact(artifact)

    def get_artifact(self, artifact_id: str) -> ArtifactRecord:
        """Retrieve and log an artifact lookup."""

        self._logger.info("Retrieving artifact for artifact_id=%s", artifact_id)
        return self._store.get_artifact(artifact_id)

    def update_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        """Update and log an existing artifact."""

        self._logger.info("Updating artifact for artifact_id=%s", artifact.artifact_id)
        return self._store.update_artifact(artifact)

    def delete_artifact(self, artifact_id: str) -> None:
        """Delete and log an artifact."""

        self._logger.info("Deleting artifact for artifact_id=%s", artifact_id)
        self._store.delete_artifact(artifact_id)

    def list_artifacts(self) -> list[ArtifactRecord]:
        """List and log all stored artifacts."""

        self._logger.info("Listing all artifacts")
        return self._store.list_artifacts()
