"""Read-only document, log, and error fetchers for Part 4 Step 4."""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Sequence
from uuid import NAMESPACE_URL, uuid5

from qwen3_coder_next.local_tooling.audit import AuditRecord
from qwen3_coder_next.local_tooling.commands import CommandRunResult
from qwen3_coder_next.research.schemas import (
    RESEARCH_SCHEMA_VERSION,
    EvidenceFreshness,
    EvidenceItem,
    EvidenceProvenance,
    ResearchRequest,
    SourceHandle,
    SourcePolicy,
    SourceType,
)


class ResearchFetchError(ValueError):
    """Base error for read-only research fetching failures."""


class MalformedResearchFetchRequestError(ResearchFetchError):
    """Raised when a fetch request cannot be processed."""


class _ResearchFetchHelper:
    """Internal deterministic construction helper for research fetchers."""

    @staticmethod
    def canonical_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @staticmethod
    def digest(payload: dict[str, Any]) -> str:
        return sha256(_ResearchFetchHelper.canonical_json(payload).encode("utf-8")).hexdigest()

    @staticmethod
    def content_digest(content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()

    @classmethod
    def source_id(cls, request_id: str, source_ref: str, source_type: SourceType) -> str:
        digest = cls.digest(
            {
                "request_id": request_id,
                "source_type": source_type.value,
                "source_ref": source_ref,
            }
        )
        return f"{request_id}-source-{uuid5(NAMESPACE_URL, digest)}"

    @classmethod
    def source_handle(
        cls,
        *,
        request_id: str,
        source_ref: str,
        display_name: str,
        source_type: SourceType,
        content: str,
        metadata: dict[str, Any],
    ) -> SourceHandle:
        return SourceHandle(
            source_id=cls.source_id(request_id, source_ref, source_type),
            source_type=source_type,
            source_ref=source_ref,
            display_name=display_name,
            metadata={**metadata, "digest": cls.content_digest(content)},
        )

    @classmethod
    def evidence_item(
        cls,
        *,
        request_id: str,
        source_handle: SourceHandle,
        source_type: SourceType,
        excerpt: str,
        content: str,
        relevance_score: float,
        confidence: float,
        freshness: EvidenceFreshness,
        provenance: EvidenceProvenance,
    ) -> EvidenceItem:
        digest = cls.digest(
            {
                "request_id": request_id,
                "source_ref": source_handle.source_ref,
                "source_type": source_type.value,
                "excerpt": excerpt,
                "line_range": list(provenance.line_range) if provenance.line_range is not None else None,
                "content_digest": cls.content_digest(content),
            }
        )
        return EvidenceItem(
            evidence_id=f"{request_id}-evidence-{digest[:12]}",
            source_type=source_type,
            source_ref=source_handle.source_ref,
            excerpt=excerpt,
            relevance_score=relevance_score,
            confidence=confidence,
            freshness=freshness,
            provenance=provenance,
        )

    @staticmethod
    def empty_result(request_id: str) -> "ResearchFetchResult":
        return ResearchFetchResult(request_id=request_id, source_handles=(), evidence_items=())


@dataclass(frozen=True, slots=True)
class ResearchFetchResult:
    """Structured evidence returned by the research fetchers."""

    request_id: str
    source_handles: tuple[SourceHandle, ...]
    evidence_items: tuple[EvidenceItem, ...]
    warnings: tuple[str, ...] = ()
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the fetch result into a deterministic mapping."""

        return {
            "request_id": self.request_id,
            "source_handles": [handle.to_dict() for handle in self.source_handles],
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "warnings": list(self.warnings),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ResearchFetchResult":
        """Rehydrate a fetch result from serialized data."""

        return cls(
            request_id=str(payload["request_id"]),
            source_handles=tuple(
                SourceHandle.from_dict(item) for item in payload.get("source_handles", ())
            ),
            evidence_items=tuple(
                EvidenceItem.from_dict(item) for item in payload.get("evidence_items", ())
            ),
            warnings=tuple(str(item) for item in payload.get("warnings", ())),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class DocumentFetcher:
    """Read-only document loader backed by local filesystem references."""

    max_snippet_chars: int | None = None
    line_window: int = 2

    def fetch(
        self,
        request: ResearchRequest,
        source_policy: SourcePolicy,
        document_refs: Iterable[Path | str],
        *,
        repository_root: Path | None = None,
    ) -> ResearchFetchResult:
        """Load documents into structured evidence without mutating the repository."""

        self._validate_request(request, source_policy)
        if SourceType.DOC not in source_policy.allowed_sources:
            return _ResearchFetchHelper.empty_result(request.request_id)

        ordered_refs = self._normalize_refs(document_refs)
        evidence_items: list[EvidenceItem] = []
        source_handles: list[SourceHandle] = []
        warnings: list[str] = []
        for ref in ordered_refs:
            file_path = self._resolve_path(ref, repository_root)
            if file_path is None:
                warnings.append(f"Skipped document reference: {ref}")
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                warnings.append(
                    f"Skipped unreadable document: {file_path.as_posix()} ({exc.__class__.__name__})"
                )
                continue
            if "\x00" in content:
                warnings.append(f"Skipped binary-like document: {file_path.as_posix()}")
                continue
            source_ref = self._source_ref_for_path(file_path, repository_root)
            snippet, line_range = self._build_snippet(content, request.query_text)
            source_handle = _ResearchFetchHelper.source_handle(
                request_id=request.request_id,
                source_ref=source_ref,
                display_name=file_path.name,
                source_type=SourceType.DOC,
                content=content,
                metadata={"path": file_path.as_posix()},
            )
            evidence_items.append(
                _ResearchFetchHelper.evidence_item(
                    request_id=request.request_id,
                    source_handle=source_handle,
                    source_type=SourceType.DOC,
                    excerpt=snippet,
                    content=content,
                    relevance_score=0.9,
                    confidence=0.85,
                    freshness=EvidenceFreshness.CURRENT,
                    provenance=EvidenceProvenance(
                        tool="document_fetcher",
                        timestamp=datetime.fromtimestamp(0, UTC),
                        line_range=line_range,
                    ),
                )
            )
            source_handles.append(source_handle)
        return ResearchFetchResult(
            request_id=request.request_id,
            source_handles=tuple(source_handles),
            evidence_items=tuple(evidence_items),
            warnings=tuple(warnings),
        )

    def _validate_request(self, request: ResearchRequest, source_policy: SourcePolicy) -> None:
        if not isinstance(request, ResearchRequest):
            raise MalformedResearchFetchRequestError("Document fetch requires a ResearchRequest.")
        if not isinstance(source_policy, SourcePolicy):
            raise MalformedResearchFetchRequestError("Document fetch requires a SourcePolicy.")

    def _normalize_refs(self, refs: Iterable[Path | str]) -> tuple[str, ...]:
        if isinstance(refs, (str, bytes)):
            raise MalformedResearchFetchRequestError("Document references must be iterable paths.")
        normalized: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            ref_text = self._normalize_ref(ref)
            if ref_text and ref_text not in seen:
                normalized.append(ref_text)
                seen.add(ref_text)
        return tuple(normalized)

    def _normalize_ref(self, ref: Path | str) -> str:
        if not isinstance(ref, (Path, str)):
            raise MalformedResearchFetchRequestError("Document references must be paths or strings.")
        return " ".join(str(ref).strip().replace("\\", "/").split())

    def _resolve_path(self, ref: str, repository_root: Path | None) -> Path | None:
        path = Path(ref)
        if repository_root is not None and not path.is_absolute():
            path = repository_root / path
        resolved = path.expanduser().resolve(strict=False)
        if repository_root is not None:
            try:
                resolved.relative_to(repository_root.expanduser().resolve(strict=False))
            except ValueError:
                return None
        return resolved

    def _source_ref_for_path(self, file_path: Path, repository_root: Path | None) -> str:
        if repository_root is None:
            return file_path.as_posix()
        try:
            return file_path.relative_to(repository_root.expanduser().resolve(strict=False)).as_posix()
        except ValueError:
            return file_path.as_posix()

    def _build_snippet(self, content: str, query_text: str) -> tuple[str, tuple[int, int] | None]:
        limit = self.max_snippet_chars if self.max_snippet_chars is not None else len(content)
        lines = content.splitlines()
        tokens = self._tokenize(query_text)
        matched_index = self._find_matching_line(lines, tokens)
        if matched_index is None:
            snippet = content[:limit]
            return snippet, self._line_range_for_text(snippet)
        start = max(0, matched_index - self.line_window)
        end = min(len(lines), matched_index + self.line_window + 1)
        excerpt = "\n".join(lines[start:end])
        return excerpt[:limit], (start + 1, min(len(lines), end))

    def _tokenize(self, value: Any) -> tuple[str, ...]:
        text = str(value).strip().lower()
        if not text:
            return ()
        tokens: list[str] = []
        current: list[str] = []
        for character in text:
            if character.isalnum():
                current.append(character)
                continue
            if current:
                token = "".join(current)
                if len(token) > 1 and token not in tokens:
                    tokens.append(token)
                current = []
        if current:
            token = "".join(current)
            if len(token) > 1 and token not in tokens:
                tokens.append(token)
        return tuple(tokens)

    def _find_matching_line(self, lines: Sequence[str], tokens: tuple[str, ...]) -> int | None:
        if not tokens:
            return None
        for index, line in enumerate(lines):
            line_lower = line.lower()
            if any(token in line_lower for token in tokens):
                return index
        return None

    def _line_range_for_text(self, snippet: str) -> tuple[int, int] | None:
        if not snippet:
            return None
        return (1, snippet.count("\n") + 1)


@dataclass(frozen=True, slots=True)
class LogFetcher:
    """Read-only log and command output fetcher."""

    max_snippet_chars: int | None = None

    def fetch(
        self,
        request: ResearchRequest,
        source_policy: SourcePolicy,
        log_artifacts: Iterable[Path | str | CommandRunResult | AuditRecord],
        *,
        repository_root: Path | None = None,
    ) -> ResearchFetchResult:
        """Convert log artifacts into structured evidence."""

        self._validate_request(request, source_policy)
        if SourceType.LOG not in source_policy.allowed_sources:
            return _ResearchFetchHelper.empty_result(request.request_id)
        if isinstance(log_artifacts, (str, bytes)):
            raise MalformedResearchFetchRequestError(
                "Log artifacts must be an iterable of supported log inputs."
            )

        ordered_inputs = tuple(log_artifacts)
        evidence_items: list[EvidenceItem] = []
        source_handles: list[SourceHandle] = []
        warnings: list[str] = []
        for index, item in enumerate(ordered_inputs):
            payload = self._normalize_artifact(item, repository_root)
            if payload is None:
                warnings.append(f"Skipped log artifact: {item!r}")
                continue
            source_ref, content, display_name = payload
            source_handle = _ResearchFetchHelper.source_handle(
                request_id=request.request_id,
                source_ref=source_ref,
                display_name=display_name,
                source_type=SourceType.LOG,
                content=content,
                metadata={"index": index},
            )
            evidence_items.append(
                _ResearchFetchHelper.evidence_item(
                    request_id=request.request_id,
                    source_handle=source_handle,
                    source_type=SourceType.LOG,
                    excerpt=self._build_excerpt(content),
                    content=content,
                    relevance_score=0.8,
                    confidence=0.8,
                    freshness=EvidenceFreshness.CURRENT,
                    provenance=EvidenceProvenance(
                        tool="log_fetcher",
                        timestamp=datetime.fromtimestamp(0, UTC),
                    ),
                )
            )
            source_handles.append(source_handle)
        return ResearchFetchResult(
            request_id=request.request_id,
            source_handles=tuple(source_handles),
            evidence_items=tuple(evidence_items),
            warnings=tuple(warnings),
        )

    def _validate_request(self, request: ResearchRequest, source_policy: SourcePolicy) -> None:
        if not isinstance(request, ResearchRequest):
            raise MalformedResearchFetchRequestError("Log fetch requires a ResearchRequest.")
        if not isinstance(source_policy, SourcePolicy):
            raise MalformedResearchFetchRequestError("Log fetch requires a SourcePolicy.")

    def _normalize_artifact(
        self,
        item: Path | str | CommandRunResult | AuditRecord,
        repository_root: Path | None,
    ) -> tuple[str, str, str] | None:
        if isinstance(item, CommandRunResult):
            if item.result is None:
                return None
            content = "\n".join(
                part for part in (item.result.stdout, item.result.stderr) if part
            )
            if not content:
                return None
            return (
                f"command://{item.path.as_posix()}",
                content,
                item.result.command if item.result else "command",
            )
        if isinstance(item, AuditRecord):
            return (
                f"audit://{item.event_id}",
                json.dumps(
                    {
                        "event_id": item.event_id,
                        "request_id": item.request_id,
                        "action": item.action,
                        "subject": item.subject,
                        "status": item.status,
                        "details": item.details,
                        "metadata": item.metadata,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                ),
                item.action,
            )
        path = Path(str(item))
        if repository_root is not None and not path.is_absolute():
            path = repository_root / path
        resolved = path.expanduser().resolve(strict=False)
        if repository_root is not None:
            try:
                resolved.relative_to(repository_root.expanduser().resolve(strict=False))
            except ValueError:
                return None
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        return (resolved.as_posix(), content, resolved.name)

    def _build_excerpt(self, content: str) -> str:
        limit = self.max_snippet_chars if self.max_snippet_chars is not None else 1_200
        return content[:limit]


@dataclass(frozen=True, slots=True)
class ErrorFetcher:
    """Read-only error artifact fetcher."""

    max_snippet_chars: int | None = None

    def fetch(
        self,
        request: ResearchRequest,
        source_policy: SourcePolicy,
        error_artifacts: Iterable[str | BaseException | Path],
    ) -> ResearchFetchResult:
        """Convert error artifacts and stack traces into structured evidence."""

        self._validate_request(request, source_policy)
        if SourceType.ERROR_ARTIFACT not in source_policy.allowed_sources:
            return _ResearchFetchHelper.empty_result(request.request_id)
        if isinstance(error_artifacts, (str, bytes)):
            raise MalformedResearchFetchRequestError(
                "Error artifacts must be an iterable of supported error inputs."
            )

        ordered_inputs = tuple(error_artifacts)
        evidence_items: list[EvidenceItem] = []
        source_handles: list[SourceHandle] = []
        warnings: list[str] = []
        for index, item in enumerate(ordered_inputs):
            content, source_ref, display_name = self._normalize_error(item)
            if content is None:
                warnings.append(f"Skipped error artifact: {item!r}")
                continue
            source_handle = _ResearchFetchHelper.source_handle(
                request_id=request.request_id,
                source_ref=source_ref,
                display_name=display_name,
                source_type=SourceType.ERROR_ARTIFACT,
                content=content,
                metadata={"index": index},
            )
            evidence_items.append(
                _ResearchFetchHelper.evidence_item(
                    request_id=request.request_id,
                    source_handle=source_handle,
                    source_type=SourceType.ERROR_ARTIFACT,
                    excerpt=self._build_excerpt(content),
                    content=content,
                    relevance_score=0.7,
                    confidence=0.75,
                    freshness=EvidenceFreshness.UNKNOWN,
                    provenance=EvidenceProvenance(
                        tool="error_fetcher",
                        timestamp=datetime.fromtimestamp(0, UTC),
                    ),
                )
            )
            source_handles.append(source_handle)
        return ResearchFetchResult(
            request_id=request.request_id,
            source_handles=tuple(source_handles),
            evidence_items=tuple(evidence_items),
            warnings=tuple(warnings),
        )

    def _validate_request(self, request: ResearchRequest, source_policy: SourcePolicy) -> None:
        if not isinstance(request, ResearchRequest):
            raise MalformedResearchFetchRequestError("Error fetch requires a ResearchRequest.")
        if not isinstance(source_policy, SourcePolicy):
            raise MalformedResearchFetchRequestError("Error fetch requires a SourcePolicy.")

    def _normalize_error(self, item: str | BaseException | Path) -> tuple[str | None, str, str]:
        if isinstance(item, BaseException):
            trace = "".join(traceback.format_exception(type(item), item, item.__traceback__))
            content = trace.strip() or f"{item.__class__.__name__}: {item}"
            return content, item.__class__.__name__, item.__class__.__name__
        if isinstance(item, Path):
            path = item.expanduser().resolve(strict=False)
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return None, "", ""
            return content, path.as_posix(), path.name
        text = " ".join(str(item).strip().split())
        if not text:
            return None, "", ""
        return text, text[:80], "error-artifact"

    def _build_excerpt(self, content: str) -> str:
        limit = self.max_snippet_chars if self.max_snippet_chars is not None else 1_200
        return content[:limit]

