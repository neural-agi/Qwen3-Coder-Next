"""Read-only local repository scanning for Part 4 Step 3."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

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


class RepositoryScanError(ValueError):
    """Base error for repository scanning failures."""


class MalformedRepositoryScanRequestError(RepositoryScanError):
    """Raised when a repository scan request cannot be processed."""


@dataclass(frozen=True, slots=True)
class RepositoryScanResult:
    """Structured read-only output returned by the repository scanner."""

    request_id: str
    repository_root: Path
    candidate_paths: tuple[str, ...]
    selected_paths: tuple[str, ...]
    source_handles: tuple[SourceHandle, ...]
    evidence_items: tuple[EvidenceItem, ...]
    repository_metadata: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the scan result into a deterministic mapping."""

        return {
            "request_id": self.request_id,
            "repository_root": self.repository_root.as_posix(),
            "candidate_paths": list(self.candidate_paths),
            "selected_paths": list(self.selected_paths),
            "source_handles": [handle.to_dict() for handle in self.source_handles],
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "repository_metadata": dict(self.repository_metadata),
            "warnings": list(self.warnings),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RepositoryScanResult":
        """Rehydrate a scan result from serialized data."""

        return cls(
            request_id=str(payload["request_id"]),
            repository_root=Path(str(payload["repository_root"])),
            candidate_paths=tuple(str(item) for item in payload.get("candidate_paths", ())),
            selected_paths=tuple(str(item) for item in payload.get("selected_paths", ())),
            source_handles=tuple(
                SourceHandle.from_dict(item) for item in payload.get("source_handles", ())
            ),
            evidence_items=tuple(
                EvidenceItem.from_dict(item) for item in payload.get("evidence_items", ())
            ),
            repository_metadata=dict(payload.get("repository_metadata", {})),
            warnings=tuple(str(item) for item in payload.get("warnings", ())),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class LocalRepositoryScanner:
    """Deterministic read-only scanner for repository evidence discovery."""

    max_file_size_bytes: int = 5 * 1024 * 1024
    include_hidden: bool = False
    ignored_directories: tuple[str, ...] = (
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
    )
    supported_suffixes: tuple[str, ...] = (
        ".py",
        ".md",
        ".rst",
        ".txt",
        ".toml",
        ".json",
        ".yaml",
        ".yml",
        ".ini",
        ".cfg",
    )
    max_file_count: int | None = None
    max_snippet_chars: int | None = None
    snippet_line_window: int = 2

    def scan(
        self,
        repository_root: Path | str,
        request: ResearchRequest,
        source_policy: SourcePolicy,
    ) -> RepositoryScanResult:
        """Walk a repository and convert local files into research evidence."""

        root_path = self._normalize_root(repository_root)
        self._validate_inputs(root_path, request, source_policy)
        source_allowed = SourceType.REPO_FILE in source_policy.allowed_sources
        if not source_allowed:
            return RepositoryScanResult(
                request_id=request.request_id,
                repository_root=root_path,
                candidate_paths=(),
                selected_paths=(),
                source_handles=(
                    SourceHandle(
                        source_id=self._build_source_id(request.request_id, root_path, "."),
                        source_type=SourceType.REPO_FOLDER,
                        source_ref=".",
                        display_name=root_path.name or root_path.as_posix(),
                        metadata={"root": root_path.as_posix()},
                    ),
                ),
                evidence_items=(),
                repository_metadata=self._build_metadata(
                    root_path,
                    (),
                    (),
                    source_policy,
                    0,
                    0,
                    0,
                    0,
                ),
            )

        candidate_paths, ignored_file_count, oversized_file_count, scan_warnings = self._collect_candidate_paths(
            root_path
        )
        selected_paths, selected_content, scan_warnings = self._select_paths(
            root_path,
            request,
            candidate_paths,
            source_policy,
            scan_warnings,
        )
        source_handles: list[SourceHandle] = [
            SourceHandle(
                source_id=self._build_source_id(request.request_id, root_path, "."),
                source_type=SourceType.REPO_FOLDER,
                source_ref=".",
                display_name=root_path.name or root_path.as_posix(),
                metadata={"root": root_path.as_posix()},
            )
        ]
        evidence_items: list[EvidenceItem] = []
        warnings: list[str] = list(scan_warnings)
        for relative_path in selected_paths:
            content = selected_content.get(relative_path)
            if content is None:
                continue

            snippet, line_range, matched_terms = self._build_snippet(content, request)
            source_handle = self._build_file_source_handle(
                request.request_id,
                root_path,
                relative_path,
                content,
            )
            evidence_item = self._build_evidence_item(
                request=request,
                relative_path=relative_path,
                source_handle=source_handle,
                excerpt=snippet,
                line_range=line_range,
                matched_terms=matched_terms,
                content=content,
            )
            source_handles.append(source_handle)
            evidence_items.append(evidence_item)

        metadata = self._build_metadata(
            root_path,
            candidate_paths,
            selected_paths,
            source_policy,
            len(evidence_items),
            len(warnings),
            ignored_file_count,
            oversized_file_count,
        )
        return RepositoryScanResult(
            request_id=request.request_id,
            repository_root=root_path,
            candidate_paths=tuple(candidate_paths),
            selected_paths=tuple(selected_paths),
            source_handles=tuple(source_handles),
            evidence_items=tuple(evidence_items),
            repository_metadata=metadata,
            warnings=tuple(warnings),
        )

    def _normalize_root(self, repository_root: Path | str) -> Path:
        if not isinstance(repository_root, (Path, str)):
            raise MalformedRepositoryScanRequestError(
                "Repository root must be a pathlib.Path or string value."
            )
        root_path = Path(repository_root).expanduser().resolve(strict=False)
        if not root_path.exists() or not root_path.is_dir():
            raise MalformedRepositoryScanRequestError(
                "Repository root must reference an existing directory."
            )
        return root_path

    def _validate_inputs(
        self,
        repository_root: Path,
        request: ResearchRequest,
        source_policy: SourcePolicy,
    ) -> None:
        if not isinstance(request, ResearchRequest):
            raise MalformedRepositoryScanRequestError(
                "Repository scan requires a ResearchRequest."
            )
        if not isinstance(source_policy, SourcePolicy):
            raise MalformedRepositoryScanRequestError(
                "Repository scan requires a SourcePolicy."
            )
        if not repository_root.exists() or not repository_root.is_dir():
            raise MalformedRepositoryScanRequestError(
                "Repository root must reference an existing directory."
            )

    def _collect_candidate_paths(self, repository_root: Path) -> tuple[tuple[str, ...], int, int, tuple[str, ...]]:
        candidates: list[str] = []
        ignored_count = 0
        oversized_count = 0
        warnings: list[str] = []
        for path in sorted(repository_root.rglob("*"), key=lambda item: item.relative_to(repository_root).as_posix()):
            if path.is_dir():
                continue
            relative_path = path.relative_to(repository_root)
            if not self.include_hidden and self._is_hidden(relative_path):
                ignored_count += 1
                continue
            if self._is_ignored_directory(relative_path):
                ignored_count += 1
                continue
            if not self._is_supported_file(path):
                ignored_count += 1
                continue
            try:
                if path.stat().st_size > self.max_file_size_bytes:
                    oversized_count += 1
                    warnings.append(f"Skipped oversized file: {relative_path}")
                    continue
            except OSError:
                ignored_count += 1
                continue
            candidates.append(relative_path.as_posix())
        return tuple(candidates), ignored_count, oversized_count, tuple(warnings)

    def _select_paths(
        self,
        repository_root: Path,
        request: ResearchRequest,
        candidate_paths: tuple[str, ...],
        source_policy: SourcePolicy,
        initial_warnings: tuple[str, ...] = (),
    ) -> tuple[tuple[str, ...], dict[str, str], tuple[str, ...]]:
        max_file_count = self._resolve_max_file_count(request, source_policy)
        if max_file_count <= 0:
            return (), {}, initial_warnings
        if not candidate_paths:
            return (), {}, initial_warnings

        path_filters = self._build_path_filters(request)
        content_tokens = self._build_content_tokens(request)
        scored: list[tuple[int, str]] = []
        content_cache: dict[str, str] = {}
        warnings: list[str] = list(initial_warnings)
        for relative_path in candidate_paths:
            score, warning = self._score_candidate(
                repository_root,
                relative_path,
                path_filters,
                content_tokens,
                content_cache,
            )
            if warning is not None:
                warnings.append(warning)
            if score > 0:
                scored.append((score, relative_path))
        if scored:
            ordered = [path for _, path in sorted(scored, key=lambda item: (-item[0], item[1]))]
            return tuple(ordered[:max_file_count]), content_cache, tuple(warnings)
        if path_filters:
            return (), content_cache, tuple(warnings)
        return tuple(candidate_paths[:max_file_count]), content_cache, tuple(warnings)

    def _resolve_max_file_count(self, request: ResearchRequest, source_policy: SourcePolicy) -> int:
        budget_limit = max(0, int(request.budget.source_limit))
        policy_limit = max(0, int(source_policy.max_evidence_items))
        limit = min(budget_limit, policy_limit)
        if self.max_file_count is not None:
            limit = min(limit, max(0, int(self.max_file_count)))
        return limit

    def _score_candidate(
        self,
        repository_root: Path,
        relative_path: str,
        path_filters: tuple[str, ...],
        content_tokens: tuple[str, ...],
        content_cache: dict[str, str],
    ) -> tuple[int, str | None]:
        path_text = relative_path.lower()
        if path_filters and not any(path_filter in path_text for path_filter in path_filters):
            return 0, None
        if not path_filters and not content_tokens:
            return 1, None
        score = 1 if path_filters else 0
        if content_tokens and any(token in path_text for token in content_tokens):
            return max(score, 3), None
        try:
            content_text = content_cache.get(relative_path)
            if content_text is None:
                raw_content = (repository_root / relative_path).read_text(encoding="utf-8", errors="replace")
                content_cache[relative_path] = raw_content
                content_text = raw_content.lower()
            else:
                content_text = content_text.lower()
        except OSError as exc:
            return score, f"Skipped unreadable file: {relative_path} ({exc.__class__.__name__})"
        if "\x00" in content_text:
            return score, f"Skipped binary-like file: {relative_path}"
        if content_tokens and any(token in content_text for token in content_tokens):
            return max(score, 2), None
        return score, None

    def _build_content_tokens(self, request: ResearchRequest) -> tuple[str, ...]:
        tokens: list[str] = []
        for value in (request.query_text, request.target_repo):
            for token in self._tokenize(value):
                if token not in tokens:
                    tokens.append(token)
        for value in (*request.constraints, *request.hints):
            if self._looks_like_path_filter(value):
                continue
            for token in self._tokenize(value):
                if token not in tokens:
                    tokens.append(token)
        return tuple(tokens)

    def _build_path_filters(self, request: ResearchRequest) -> tuple[str, ...]:
        filters: list[str] = []
        for value in (*request.constraints, *request.hints):
            normalized = self._normalize_filter_value(value)
            if not normalized or not self._looks_like_path_filter(normalized):
                continue
            if normalized not in filters:
                filters.append(normalized)
        return tuple(filters)

    def _normalize_filter_value(self, value: Any) -> str:
        return " ".join(str(value).strip().replace("\\", "/").split()).lower()

    def _looks_like_path_filter(self, value: Any) -> bool:
        text = str(value)
        return any(character in text for character in ("/", "\\", ".", "*", "?"))

    def _tokenize(self, value: Any) -> tuple[str, ...]:
        text = str(value).strip().lower()
        if not text:
            return ()
        normalized = []
        current = []
        for character in text:
            if character.isalnum():
                current.append(character)
                continue
            if current:
                token = "".join(current)
                if len(token) > 1 and token not in normalized:
                    normalized.append(token)
                current = []
        if current:
            token = "".join(current)
            if len(token) > 1 and token not in normalized:
                normalized.append(token)
        return tuple(normalized)

    def _build_snippet(self, content: str, request: ResearchRequest) -> tuple[str, tuple[int, int] | None, tuple[str, ...]]:
        limit = self._resolve_snippet_limit(request)
        lines = content.splitlines()
        tokens = self._build_content_tokens(request)
        matched_index = self._find_matching_line(lines, tokens)
        if matched_index is None:
            snippet = content[:limit]
            return snippet, self._line_range_for_text(snippet), ()

        start = max(0, matched_index - self.snippet_line_window)
        end = min(len(lines), matched_index + self.snippet_line_window + 1)
        excerpt_lines = lines[start:end]
        snippet = "\n".join(excerpt_lines)[:limit]
        matched_terms = tuple(token for token in tokens if any(token in line.lower() for line in excerpt_lines))
        return snippet, (start + 1, min(len(lines), end)), matched_terms

    def _resolve_snippet_limit(self, request: ResearchRequest) -> int:
        limit = max(0, int(request.budget.snippet_limit))
        if self.max_snippet_chars is not None:
            limit = min(limit, max(0, int(self.max_snippet_chars)))
        return limit

    def _find_matching_line(self, lines: list[str], tokens: tuple[str, ...]) -> int | None:
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
        line_count = snippet.count("\n") + 1
        return (1, line_count)

    def _build_source_id(self, request_id: str, repository_root: Path, relative_path: str) -> str:
        canonical_json = json.dumps(
            {
                "request_id": request_id,
                "repository_root": repository_root.as_posix(),
                "relative_path": relative_path,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        digest = sha256(canonical_json.encode("utf-8")).hexdigest()
        return f"{request_id}-source-{uuid5(NAMESPACE_URL, digest)}"

    def _build_file_source_handle(
        self,
        request_id: str,
        repository_root: Path,
        relative_path: str,
        content: str,
    ) -> SourceHandle:
        return SourceHandle(
            source_id=self._build_source_id(request_id, repository_root, relative_path),
            source_type=SourceType.REPO_FILE,
            source_ref=relative_path,
            display_name=Path(relative_path).name,
            metadata={
                "path": relative_path,
                "size": len(content),
                "digest": sha256(content.encode("utf-8")).hexdigest(),
            },
        )

    def _build_evidence_item(
        self,
        *,
        request: ResearchRequest,
        relative_path: str,
        source_handle: SourceHandle,
        excerpt: str,
        line_range: tuple[int, int] | None,
        matched_terms: tuple[str, ...],
        content: str,
    ) -> EvidenceItem:
        canonical_json = json.dumps(
            {
                "request_id": request.request_id,
                "relative_path": relative_path,
                "source_ref": source_handle.source_ref,
                "excerpt": excerpt,
                "line_range": list(line_range) if line_range is not None else None,
                "matched_terms": list(matched_terms),
                "content_digest": sha256(content.encode("utf-8")).hexdigest(),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        digest = sha256(canonical_json.encode("utf-8")).hexdigest()
        relevance = 1.0 if matched_terms else 0.75
        confidence = 0.95 if matched_terms else 0.8
        provenance = EvidenceProvenance(
            tool="local_repository_scanner",
            timestamp=datetime.fromtimestamp(0, UTC),
            line_range=line_range,
        )
        return EvidenceItem(
            evidence_id=f"{request.request_id}-evidence-{digest[:12]}",
            source_type=SourceType.REPO_FILE,
            source_ref=relative_path,
            excerpt=excerpt,
            relevance_score=relevance,
            confidence=confidence,
            freshness=EvidenceFreshness.CURRENT,
            provenance=provenance,
        )

    def _build_metadata(
        self,
        repository_root: Path,
        candidate_paths: tuple[str, ...],
        selected_paths: tuple[str, ...],
        source_policy: SourcePolicy,
        evidence_count: int,
        warning_count: int,
        ignored_file_count: int,
        oversized_file_count: int,
    ) -> dict[str, Any]:
        top_level_entries = self._collect_top_level_entries(repository_root)
        return {
            "repository_name": repository_root.name or repository_root.as_posix(),
            "repository_root": repository_root.as_posix(),
            "candidate_file_count": len(candidate_paths),
            "selected_file_count": len(selected_paths),
            "evidence_count": evidence_count,
            "warning_count": warning_count,
            "ignored_file_count": ignored_file_count,
            "oversized_file_count": oversized_file_count,
            "top_level_entries": list(top_level_entries),
            "allowed_sources": [item.value for item in source_policy.allowed_sources],
            "preferred_sources": [item.value for item in source_policy.preferred_sources],
            "blocked_sources": [item.value for item in source_policy.blocked_sources],
        }

    def _collect_top_level_entries(self, repository_root: Path) -> tuple[str, ...]:
        entries = []
        for path in sorted(repository_root.iterdir(), key=lambda item: item.name.lower()):
            entries.append(path.name)
        return tuple(entries)

    def _is_ignored_directory(self, relative_path: Path) -> bool:
        return any(part in self.ignored_directories for part in relative_path.parts[:-1])

    def _is_supported_file(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if self.supported_suffixes and path.suffix.lower() not in self.supported_suffixes:
            return False
        return True

    def _is_hidden(self, relative_path: Path) -> bool:
        return any(part.startswith(".") for part in relative_path.parts)


def scan_local_repository(
    repository_root: Path | str,
    request: ResearchRequest,
    source_policy: SourcePolicy,
) -> RepositoryScanResult:
    """Scan a repository using the default local repository scanner."""

    return LocalRepositoryScanner().scan(repository_root, request, source_policy)
