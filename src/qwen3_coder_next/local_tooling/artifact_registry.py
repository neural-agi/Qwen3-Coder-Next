"""Artifact registry abstractions for the local tooling layer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any

from qwen3_coder_next.local_tooling.contracts import ArtifactManifest, ArtifactProvenance


class ArtifactRegistryErrorCode(StrEnum):
    """Structured error codes for artifact registry operations."""

    DUPLICATE_MANIFEST = "duplicate_manifest"
    MANIFEST_NOT_FOUND = "manifest_not_found"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    INVALID_MANIFEST = "invalid_manifest"
    PERSISTENCE_FAILED = "persistence_failed"


class ArtifactRegistryError(Exception):
    """Structured registry error with a stable error code."""

    def __init__(
        self,
        error_code: ArtifactRegistryErrorCode,
        message: str,
        *,
        request_id: str | None = None,
        manifest_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.request_id = request_id
        self.manifest_id = manifest_id


@dataclass(frozen=True, slots=True)
class ArtifactRegistryRequest:
    """Immutable request for registering or updating a manifest."""

    request_id: str
    artifact_id: str
    name: str
    location: Path
    artifact_type: str
    content: str
    provenance: ArtifactProvenance
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ArtifactRegistryResult:
    """Immutable result returned by an artifact registry."""

    request_id: str
    manifest: ArtifactManifest | None
    success: bool
    error_code: ArtifactRegistryErrorCode | None = None
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ArtifactRegistry(ABC):
    """Abstract artifact registry interface."""

    @abstractmethod
    def register(self, request: ArtifactRegistryRequest) -> ArtifactRegistryResult:
        """Register a new artifact manifest."""

    @abstractmethod
    def supersede(self, manifest_id: str, request: ArtifactRegistryRequest) -> ArtifactRegistryResult:
        """Create a new manifest that supersedes an existing one."""

    @abstractmethod
    def archive(self, manifest_id: str, request_id: str) -> ArtifactRegistryResult:
        """Archive an existing manifest."""

    @abstractmethod
    def get(self, manifest_id: str) -> ArtifactManifest:
        """Return a manifest by identifier."""

    @abstractmethod
    def list(self) -> list[ArtifactManifest]:
        """Return all manifests in deterministic order."""

    @abstractmethod
    def history(self, artifact_id: str) -> list[ArtifactManifest]:
        """Return the full manifest history for an artifact identifier."""


class DeterministicArtifactRegistry(ArtifactRegistry):
    """Deterministic JSON-backed artifact registry."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path
        self._manifests: list[ArtifactManifest] = []
        self._load_error: ArtifactRegistryError | None = None
        self._load()

    def register(self, request: ArtifactRegistryRequest) -> ArtifactRegistryResult:
        """Register a new immutable manifest."""

        if self._load_error is not None:
            return self._reject(
                request.request_id,
                self._load_error.error_code,
                str(self._load_error),
                request.metadata,
            )
        if self._find_manifest(request.artifact_id) is not None:
            return self._reject(
                request.request_id,
                ArtifactRegistryErrorCode.DUPLICATE_MANIFEST,
                "Artifact already has a manifest in the registry.",
                request.metadata,
            )
        try:
            manifest = self._build_manifest(request)
        except ArtifactRegistryError as error:
            return self._reject(request.request_id, error.error_code, str(error), request.metadata)
        previous_manifests = list(self._manifests)
        self._manifests.append(manifest)
        save_error = self._save()
        if save_error is not None:
            self._manifests = previous_manifests
            return self._reject(request.request_id, save_error.error_code, str(save_error), request.metadata)
        return ArtifactRegistryResult(request_id=request.request_id, manifest=manifest, success=True, metadata=request.metadata)

    def supersede(self, manifest_id: str, request: ArtifactRegistryRequest) -> ArtifactRegistryResult:
        """Create a new manifest that supersedes an existing manifest."""

        if self._load_error is not None:
            return self._reject(
                request.request_id,
                self._load_error.error_code,
                str(self._load_error),
                request.metadata,
            )
        prior = self._find_manifest_by_id(manifest_id)
        if prior is None:
            return self._reject(
                request.request_id,
                ArtifactRegistryErrorCode.MANIFEST_NOT_FOUND,
                "Manifest not found.",
                request.metadata,
            )
        try:
            manifest = self._build_manifest(
                request,
                supersedes_manifest_id=prior.manifest_id,
            )
        except ArtifactRegistryError as error:
            return self._reject(request.request_id, error.error_code, str(error), request.metadata)
        previous_manifests = list(self._manifests)
        self._manifests.append(manifest)
        self._manifests = [
            item if item.manifest_id != prior.manifest_id else self._archive_copy(item)
            for item in self._manifests
        ]
        save_error = self._save()
        if save_error is not None:
            self._manifests = previous_manifests
            return self._reject(request.request_id, save_error.error_code, str(save_error), request.metadata)
        return ArtifactRegistryResult(request_id=request.request_id, manifest=manifest, success=True, metadata=request.metadata)

    def archive(self, manifest_id: str, request_id: str) -> ArtifactRegistryResult:
        """Archive an existing manifest without mutating historical data in place."""

        if self._load_error is not None:
            return self._reject(
                request_id,
                self._load_error.error_code,
                str(self._load_error),
            )
        manifest = self._find_manifest_by_id(manifest_id)
        if manifest is None:
            return self._reject(
                request_id,
                ArtifactRegistryErrorCode.MANIFEST_NOT_FOUND,
                "Manifest not found.",
            )
        archived = self._archive_copy(manifest)
        self._replace_manifest(archived)
        save_error = self._save()
        if save_error is not None:
            self._replace_manifest(manifest)
            return self._reject(request_id, save_error.error_code, str(save_error))
        return ArtifactRegistryResult(request_id=request_id, manifest=archived, success=True)

    def get(self, manifest_id: str) -> ArtifactManifest:
        """Return a manifest by identifier."""

        if self._load_error is not None:
            raise self._load_error
        manifest = self._find_manifest_by_id(manifest_id)
        if manifest is None:
            raise ArtifactRegistryError(
                ArtifactRegistryErrorCode.MANIFEST_NOT_FOUND,
                f"Manifest not found for manifest_id={manifest_id!r}.",
                manifest_id=manifest_id,
            )
        return manifest

    def list(self) -> list[ArtifactManifest]:
        """Return all manifests in deterministic order."""

        if self._load_error is not None:
            raise self._load_error
        return sorted(self._manifests, key=lambda item: (item.artifact_id, item.created_at, item.manifest_id))

    def history(self, artifact_id: str) -> list[ArtifactManifest]:
        """Return all manifests for a specific artifact."""

        if self._load_error is not None:
            raise self._load_error
        return [manifest for manifest in self.list() if manifest.artifact_id == artifact_id]

    def _build_manifest(
        self,
        request: ArtifactRegistryRequest,
        *,
        supersedes_manifest_id: str | None = None,
    ) -> ArtifactManifest:
        checksum = sha256(request.content.encode("utf-8")).hexdigest()
        expected_checksum = request.metadata.get("expected_content_checksum")
        if expected_checksum is not None and str(expected_checksum) != checksum:
            raise ArtifactRegistryError(
                ArtifactRegistryErrorCode.CHECKSUM_MISMATCH,
                "Content checksum did not match the expected checksum.",
                request_id=request.request_id,
            )
        return ArtifactManifest(
            manifest_id=self._manifest_identity(request, checksum, supersedes_manifest_id=supersedes_manifest_id),
            artifact_id=request.artifact_id,
            name=request.name,
            location=request.location,
            artifact_type=request.artifact_type,
            content_checksum=checksum,
            checksum_algorithm="sha256",
            provenance=request.provenance,
            created_at=request.provenance.timestamp,
            supersedes_manifest_id=supersedes_manifest_id,
            archived=False,
            metadata=request.metadata,
        )

    def _manifest_identity(
        self,
        request: ArtifactRegistryRequest,
        checksum: str,
        *,
        supersedes_manifest_id: str | None = None,
    ) -> str:
        identity_source = "|".join(
            [
                request.artifact_id,
                checksum,
                request.provenance.request_id,
                supersedes_manifest_id or "",
            ]
        )
        return f"manifest-{sha256(identity_source.encode('utf-8')).hexdigest()}"

    def _archive_copy(self, manifest: ArtifactManifest) -> ArtifactManifest:
        return ArtifactManifest(
            manifest_id=manifest.manifest_id,
            artifact_id=manifest.artifact_id,
            name=manifest.name,
            location=manifest.location,
            artifact_type=manifest.artifact_type,
            content_checksum=manifest.content_checksum,
            checksum_algorithm=manifest.checksum_algorithm,
            provenance=manifest.provenance,
            created_at=manifest.created_at,
            supersedes_manifest_id=manifest.supersedes_manifest_id,
            archived=True,
            metadata=manifest.metadata,
        )

    def _replace_manifest(self, updated: ArtifactManifest) -> None:
        self._manifests = [updated if item.manifest_id == updated.manifest_id else item for item in self._manifests]

    def _find_manifest(self, artifact_id: str) -> ArtifactManifest | None:
        for manifest in self._manifests:
            if manifest.artifact_id == artifact_id and not manifest.archived:
                return manifest
        return None

    def _find_manifest_by_id(self, manifest_id: str) -> ArtifactManifest | None:
        for manifest in self._manifests:
            if manifest.manifest_id == manifest_id:
                return manifest
        return None

    def _reject(
        self,
        request_id: str,
        error_code: ArtifactRegistryErrorCode,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRegistryResult:
        return ArtifactRegistryResult(
            request_id=request_id,
            manifest=None,
            success=False,
            error_code=error_code,
            error_message=message,
            metadata=metadata or {},
        )

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        import json

        try:
            with self._storage_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, list):
                raise ArtifactRegistryError(
                    ArtifactRegistryErrorCode.INVALID_MANIFEST,
                    "Persisted artifact registry payload must be a list of manifests.",
                )
            self._manifests = [self._deserialize_manifest(item) for item in payload]
        except ArtifactRegistryError as error:
            self._manifests = []
            self._load_error = error
        except (OSError, ValueError, TypeError) as error:
            self._manifests = []
            self._load_error = ArtifactRegistryError(
                ArtifactRegistryErrorCode.PERSISTENCE_FAILED,
                f"Failed to load artifact registry: {error}.",
            )

    def _save(self) -> ArtifactRegistryError | None:
        if self._storage_path is None:
            return None
        import json

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            with self._storage_path.open("w", encoding="utf-8") as handle:
                json.dump([self._serialize_manifest(item) for item in self.list()], handle, indent=2)
        except OSError as error:
            return ArtifactRegistryError(
                ArtifactRegistryErrorCode.PERSISTENCE_FAILED,
                f"Failed to persist artifact registry: {error}.",
            )
        return None

    def _serialize_manifest(self, manifest: ArtifactManifest) -> dict[str, object]:
        return {
            "manifest_id": manifest.manifest_id,
            "artifact_id": manifest.artifact_id,
            "name": manifest.name,
            "location": str(manifest.location),
            "artifact_type": manifest.artifact_type,
            "content_checksum": manifest.content_checksum,
            "checksum_algorithm": manifest.checksum_algorithm,
            "provenance": {
                "request_id": manifest.provenance.request_id,
                "operation": manifest.provenance.operation,
                "source": manifest.provenance.source,
                "timestamp": manifest.provenance.timestamp.isoformat(),
                "metadata": manifest.provenance.metadata,
            },
            "created_at": manifest.created_at.isoformat(),
            "supersedes_manifest_id": manifest.supersedes_manifest_id,
            "archived": manifest.archived,
            "metadata": manifest.metadata,
        }

    def _deserialize_manifest(self, payload: dict[str, object]) -> ArtifactManifest:
        from datetime import datetime

        if not isinstance(payload, dict):
            raise ArtifactRegistryError(
                ArtifactRegistryErrorCode.INVALID_MANIFEST,
                "Persisted manifest payload must be a mapping.",
            )
        required_keys = (
            "manifest_id",
            "artifact_id",
            "name",
            "location",
            "artifact_type",
            "content_checksum",
            "checksum_algorithm",
            "provenance",
            "created_at",
        )
        if any(key not in payload for key in required_keys):
            raise ArtifactRegistryError(
                ArtifactRegistryErrorCode.INVALID_MANIFEST,
                "Persisted manifest payload is missing required fields.",
            )
        provenance_payload = payload["provenance"]
        if not isinstance(provenance_payload, dict):
            raise ArtifactRegistryError(
                ArtifactRegistryErrorCode.INVALID_MANIFEST,
                "Persisted manifest provenance must be a mapping.",
            )
        provenance_required_keys = ("request_id", "operation", "source", "timestamp")
        if any(key not in provenance_payload for key in provenance_required_keys):
            raise ArtifactRegistryError(
                ArtifactRegistryErrorCode.INVALID_MANIFEST,
                "Persisted manifest provenance is missing required fields.",
            )
        return ArtifactManifest(
            manifest_id=str(payload["manifest_id"]),
            artifact_id=str(payload["artifact_id"]),
            name=str(payload["name"]),
            location=Path(str(payload["location"])),
            artifact_type=str(payload["artifact_type"]),
            content_checksum=str(payload["content_checksum"]),
            checksum_algorithm=str(payload["checksum_algorithm"]),
            provenance=ArtifactProvenance(
                request_id=str(provenance_payload["request_id"]),
                operation=str(provenance_payload["operation"]),
                source=str(provenance_payload["source"]),
                timestamp=datetime.fromisoformat(str(provenance_payload["timestamp"])),
                metadata=dict(provenance_payload.get("metadata", {})),
            ),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            supersedes_manifest_id=payload.get("supersedes_manifest_id") or None,
            archived=bool(payload.get("archived", False)),
            metadata=dict(payload.get("metadata", {})),
        )
