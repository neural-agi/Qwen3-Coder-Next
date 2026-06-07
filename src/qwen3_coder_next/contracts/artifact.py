"""Artifact contract definitions."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ArtifactType(StrEnum):
    """Supported artifact categories."""

    FILE = "file"
    REPORT = "report"
    SNAPSHOT = "snapshot"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    """Immutable description of a created artifact."""

    artifact_id: str
    artifact_type: ArtifactType
    path: str
    created_at: datetime
