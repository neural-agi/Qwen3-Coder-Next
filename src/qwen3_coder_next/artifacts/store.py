"""Dictionary-backed in-memory artifact storage."""

from qwen3_coder_next.artifacts.exceptions import (
    ArtifactNotFoundError,
    DuplicateArtifactError,
)
from qwen3_coder_next.contracts import ArtifactRecord


class ArtifactStore:
    """In-memory store for artifact records."""

    def __init__(self) -> None:
        """Initialize the in-memory artifact store."""

        self._artifacts: dict[str, ArtifactRecord] = {}

    def create_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        """Create a new artifact entry."""

        if artifact.artifact_id in self._artifacts:
            raise DuplicateArtifactError(
                f"Artifact already exists for artifact_id={artifact.artifact_id!r}."
            )
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def get_artifact(self, artifact_id: str) -> ArtifactRecord:
        """Return a stored artifact by artifact identifier."""

        try:
            return self._artifacts[artifact_id]
        except KeyError as exc:
            raise ArtifactNotFoundError(
                f"Artifact not found for artifact_id={artifact_id!r}."
            ) from exc

    def update_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        """Replace an existing artifact entry."""

        if artifact.artifact_id not in self._artifacts:
            raise ArtifactNotFoundError(
                f"Artifact not found for artifact_id={artifact.artifact_id!r}."
            )
        self._artifacts[artifact.artifact_id] = artifact
        return artifact

    def delete_artifact(self, artifact_id: str) -> None:
        """Delete a stored artifact by artifact identifier."""

        if artifact_id not in self._artifacts:
            raise ArtifactNotFoundError(
                f"Artifact not found for artifact_id={artifact_id!r}."
            )
        del self._artifacts[artifact_id]

    def list_artifacts(self) -> list[ArtifactRecord]:
        """Return all stored artifacts."""

        return list(self._artifacts.values())
