"""Dictionary-backed artifact storage with optional filesystem persistence."""

import json
from pathlib import Path

from qwen3_coder_next.artifacts.exceptions import (
    ArtifactNotFoundError,
    DuplicateArtifactError,
)
from qwen3_coder_next.contracts import ArtifactRecord


class ArtifactStore:
    """Store for artifact records."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize the artifact store."""

        self._storage_path = storage_path
        self._artifacts: dict[str, ArtifactRecord] = {}
        self._load_from_disk()

    def create_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        """Create a new artifact entry."""

        if artifact.artifact_id in self._artifacts:
            raise DuplicateArtifactError(
                f"Artifact already exists for artifact_id={artifact.artifact_id!r}."
            )
        self._artifacts[artifact.artifact_id] = artifact
        self._save_to_disk()
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
        self._save_to_disk()
        return artifact

    def delete_artifact(self, artifact_id: str) -> None:
        """Delete a stored artifact by artifact identifier."""

        if artifact_id not in self._artifacts:
            raise ArtifactNotFoundError(
                f"Artifact not found for artifact_id={artifact_id!r}."
            )
        del self._artifacts[artifact_id]
        self._save_to_disk()

    def list_artifacts(self) -> list[ArtifactRecord]:
        """Return all stored artifacts."""

        return list(self._artifacts.values())

    def _load_from_disk(self) -> None:
        """Load persisted artifact entries if a storage path is configured."""

        if self._storage_path is None or not self._storage_path.exists():
            return

        with self._storage_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self._artifacts = {
            item["artifact_id"]: self._deserialize_artifact(item) for item in payload
        }

    def _save_to_disk(self) -> None:
        """Persist artifact entries if a storage path is configured."""

        if self._storage_path is None:
            return

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as handle:
            json.dump([self._serialize_artifact(artifact) for artifact in self._artifacts.values()], handle, indent=2)

    def _serialize_artifact(self, artifact: ArtifactRecord) -> dict[str, object]:
        return {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type.value,
            "path": artifact.path,
            "created_at": artifact.created_at.isoformat(),
        }

    def _deserialize_artifact(self, payload: dict[str, object]) -> ArtifactRecord:
        from datetime import datetime

        from qwen3_coder_next.contracts import ArtifactType

        return ArtifactRecord(
            artifact_id=str(payload["artifact_id"]),
            artifact_type=ArtifactType(str(payload["artifact_type"])),
            path=str(payload["path"]),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
        )
