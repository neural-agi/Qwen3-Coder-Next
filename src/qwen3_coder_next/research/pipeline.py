"""Deterministic research pipeline orchestration for Part 4 Step 7."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from qwen3_coder_next.local_tooling.audit import AuditRecord
from qwen3_coder_next.local_tooling.commands import CommandRunResult
from qwen3_coder_next.research.evidence import (
    ResearchEvidenceNormalizationResult,
    ResearchEvidenceNormalizer,
)
from qwen3_coder_next.research.fetchers import (
    DocumentFetcher,
    ErrorFetcher,
    LogFetcher,
    ResearchFetchResult,
)
from qwen3_coder_next.research.packet_assembly import (
    ResearchPacketAssembler,
)
from qwen3_coder_next.research.scanner import (
    LocalRepositoryScanner,
    RepositoryScanResult,
)
from qwen3_coder_next.research.schemas import (
    RESEARCH_SCHEMA_VERSION,
    EvidenceItem,
    ResearchPacket,
    ResearchRequest,
    SourceHandle,
    SourcePolicy,
    SourceType,
)
from qwen3_coder_next.research.state import ResearchRevision, ResearchState


class ResearchPipelineError(ValueError):
    """Base error for research pipeline failures."""


class MalformedResearchPipelineInputError(ResearchPipelineError):
    """Raised when pipeline inputs cannot be orchestrated."""


_PIPELINE_STAGE_SCAN = "repository_scan"
_PIPELINE_STAGE_DOCUMENTS = "document_fetch"
_PIPELINE_STAGE_LOGS = "log_fetch"
_PIPELINE_STAGE_ERRORS = "error_fetch"
_PIPELINE_STAGE_NORMALIZE = "evidence_normalization"
_PIPELINE_STAGE_PACKET = "packet_assembly"


@dataclass(frozen=True, slots=True)
class ResearchPipelineResult:
    """Structured result returned by the research pipeline."""

    request: ResearchRequest
    source_policy: SourcePolicy
    stage_order: tuple[str, ...]
    repository_scan_result: RepositoryScanResult | None
    document_fetch_result: ResearchFetchResult | None
    log_fetch_result: ResearchFetchResult | None
    error_fetch_result: ResearchFetchResult | None
    evidence_normalization_result: ResearchEvidenceNormalizationResult
    research_packet: ResearchPacket
    research_state: ResearchState
    source_handles: tuple[SourceHandle, ...]
    evidence_items: tuple[EvidenceItem, ...]
    completed_at: datetime = field(default_factory=lambda: datetime.fromtimestamp(0, UTC))
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the pipeline result into a deterministic mapping."""

        return {
            "request": self.request.to_dict(),
            "source_policy": self.source_policy.to_dict(),
            "stage_order": list(self.stage_order),
            "repository_scan_result": self.repository_scan_result.to_dict()
            if self.repository_scan_result
            else None,
            "document_fetch_result": self.document_fetch_result.to_dict()
            if self.document_fetch_result
            else None,
            "log_fetch_result": self.log_fetch_result.to_dict() if self.log_fetch_result else None,
            "error_fetch_result": self.error_fetch_result.to_dict()
            if self.error_fetch_result
            else None,
            "evidence_normalization_result": self.evidence_normalization_result.to_dict(),
            "research_packet": self.research_packet.to_dict(),
            "research_state": self.research_state.to_dict(),
            "source_handles": [item.to_dict() for item in self.source_handles],
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "completed_at": self.completed_at.isoformat(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchPipelineResult":
        """Rehydrate the pipeline result from serialized data."""

        repository_scan_result = payload.get("repository_scan_result")
        document_fetch_result = payload.get("document_fetch_result")
        log_fetch_result = payload.get("log_fetch_result")
        error_fetch_result = payload.get("error_fetch_result")
        return cls(
            request=ResearchRequest.from_dict(dict(payload["request"])),
            source_policy=SourcePolicy.from_dict(dict(payload["source_policy"])),
            stage_order=tuple(str(item) for item in payload.get("stage_order", ())),
            repository_scan_result=RepositoryScanResult.from_dict(repository_scan_result)
            if repository_scan_result
            else None,
            document_fetch_result=ResearchFetchResult.from_dict(document_fetch_result)
            if document_fetch_result
            else None,
            log_fetch_result=ResearchFetchResult.from_dict(log_fetch_result)
            if log_fetch_result
            else None,
            error_fetch_result=ResearchFetchResult.from_dict(error_fetch_result)
            if error_fetch_result
            else None,
            evidence_normalization_result=ResearchEvidenceNormalizationResult.from_dict(
                dict(payload["evidence_normalization_result"])
            ),
            research_packet=ResearchPacket.from_dict(dict(payload["research_packet"])),
            research_state=ResearchState.from_dict(dict(payload["research_state"])),
            source_handles=tuple(SourceHandle.from_dict(item) for item in payload.get("source_handles", ())),
            evidence_items=tuple(EvidenceItem.from_dict(item) for item in payload.get("evidence_items", ())),
            completed_at=datetime.fromisoformat(
                str(
                    payload.get(
                        "completed_at",
                        datetime.fromtimestamp(0, UTC).isoformat(),
                    )
                )
            ),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class ResearchPipeline:
    """Coordinate the deterministic research layer stages."""

    repository_scanner: LocalRepositoryScanner = field(default_factory=LocalRepositoryScanner)
    document_fetcher: DocumentFetcher = field(default_factory=DocumentFetcher)
    log_fetcher: LogFetcher = field(default_factory=LogFetcher)
    error_fetcher: ErrorFetcher = field(default_factory=ErrorFetcher)
    evidence_normalizer: ResearchEvidenceNormalizer = field(default_factory=ResearchEvidenceNormalizer)
    packet_assembler: ResearchPacketAssembler = field(default_factory=ResearchPacketAssembler)

    def run(
        self,
        request: ResearchRequest,
        *,
        source_policy: SourcePolicy,
        repository_root: Path | str | None = None,
        document_refs: Iterable[Path | str] = (),
        log_artifacts: Iterable[Path | str | CommandRunResult | AuditRecord] = (),
        error_artifacts: Iterable[str | BaseException | Path] = (),
        research_state: ResearchState | None = None,
    ) -> ResearchPipelineResult:
        """Run the full deterministic research pipeline."""

        self._validate_inputs(request, source_policy)
        repository_root_path = Path(repository_root) if repository_root is not None else None
        state = research_state or ResearchState(state_id=f"{request.request_id}-research-state")
        state = state.with_request(request).with_source_policy(source_policy)

        stage_order: list[str] = []
        repository_scan_result: RepositoryScanResult | None = None
        document_fetch_result: ResearchFetchResult | None = None
        log_fetch_result: ResearchFetchResult | None = None
        error_fetch_result: ResearchFetchResult | None = None

        source_handles: list[SourceHandle] = list(state.selected_sources)
        evidence_sources: list[
            ResearchEvidenceNormalizationResult | ResearchFetchResult | RepositoryScanResult
        ] = []

        if repository_root_path is not None and self._allows_repo_scan(source_policy):
            repository_scan_result = self.repository_scanner.scan(
                repository_root_path,
                request,
                source_policy,
            )
            stage_order.append(_PIPELINE_STAGE_SCAN)
            source_handles.extend(repository_scan_result.source_handles)
            evidence_sources.append(repository_scan_result)

        if self._allows_documents(source_policy):
            document_fetch_result = self.document_fetcher.fetch(
                request,
                source_policy,
                document_refs,
                repository_root=repository_root_path,
            )
            stage_order.append(_PIPELINE_STAGE_DOCUMENTS)
            source_handles.extend(document_fetch_result.source_handles)
            if document_fetch_result.evidence_items:
                evidence_sources.append(document_fetch_result)

        if self._allows_logs(source_policy):
            log_fetch_result = self.log_fetcher.fetch(
                request,
                source_policy,
                log_artifacts,
                repository_root=repository_root_path,
            )
            stage_order.append(_PIPELINE_STAGE_LOGS)
            source_handles.extend(log_fetch_result.source_handles)
            if log_fetch_result.evidence_items:
                evidence_sources.append(log_fetch_result)

        if self._allows_errors(source_policy):
            error_fetch_result = self.error_fetcher.fetch(request, source_policy, error_artifacts)
            stage_order.append(_PIPELINE_STAGE_ERRORS)
            source_handles.extend(error_fetch_result.source_handles)
            if error_fetch_result.evidence_items:
                evidence_sources.append(error_fetch_result)

        evidence_normalization_result = self.evidence_normalizer.normalize(
            tuple(evidence_sources),
            request=request,
            source_policy=source_policy,
        )
        stage_order.append(_PIPELINE_STAGE_NORMALIZE)

        research_packet = self.packet_assembler.assemble(
            request,
            evidence_normalization_result,
            source_policy=source_policy,
        )
        stage_order.append(_PIPELINE_STAGE_PACKET)

        state = state.with_selected_sources(tuple(source_handles))
        for evidence_item in evidence_normalization_result.evidence_items:
            state = state.add_evidence_item(evidence_item)
        state = state.with_research_packet(research_packet)

        return ResearchPipelineResult(
            request=request,
            source_policy=source_policy,
            stage_order=tuple(stage_order),
            repository_scan_result=repository_scan_result,
            document_fetch_result=document_fetch_result,
            log_fetch_result=log_fetch_result,
            error_fetch_result=error_fetch_result,
            evidence_normalization_result=evidence_normalization_result,
            research_packet=research_packet,
            research_state=state,
            source_handles=tuple(source_handles),
            evidence_items=evidence_normalization_result.evidence_items,
        )

    def _validate_inputs(self, request: ResearchRequest, source_policy: SourcePolicy) -> None:
        if not isinstance(request, ResearchRequest):
            raise MalformedResearchPipelineInputError("Research pipeline requires a ResearchRequest.")
        if not isinstance(source_policy, SourcePolicy):
            raise MalformedResearchPipelineInputError("Research pipeline requires a SourcePolicy.")

    def _allows_repo_scan(self, source_policy: SourcePolicy) -> bool:
        return SourceType.REPO_FILE in source_policy.allowed_sources

    def _allows_documents(self, source_policy: SourcePolicy) -> bool:
        return SourceType.DOC in source_policy.allowed_sources

    def _allows_logs(self, source_policy: SourcePolicy) -> bool:
        return SourceType.LOG in source_policy.allowed_sources

    def _allows_errors(self, source_policy: SourcePolicy) -> bool:
        return SourceType.ERROR_ARTIFACT in source_policy.allowed_sources


def run_research_pipeline(
    request: ResearchRequest,
    *,
    source_policy: SourcePolicy,
    repository_root: Path | str | None = None,
    document_refs: Iterable[Path | str] = (),
    log_artifacts: Iterable[Path | str | CommandRunResult | AuditRecord] = (),
    error_artifacts: Iterable[str | BaseException | Path] = (),
    research_state: ResearchState | None = None,
) -> ResearchPipelineResult:
    """Run the deterministic research pipeline using the default orchestrator."""

    return ResearchPipeline().run(
        request,
        source_policy=source_policy,
        repository_root=repository_root,
        document_refs=document_refs,
        log_artifacts=log_artifacts,
        error_artifacts=error_artifacts,
        research_state=research_state,
    )
