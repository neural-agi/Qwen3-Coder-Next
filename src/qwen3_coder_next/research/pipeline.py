"""Deterministic research pipeline orchestration for Part 4 Step 7."""

from __future__ import annotations

import logging
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
from qwen3_coder_next.research.observability import (
    ResearchFailureRecord,
    ResearchFlowMetrics,
    ResearchPipelineObservability,
    ResearchStageTrace,
)
from qwen3_coder_next.research.scanner import (
    LocalRepositoryScanner,
    RepositoryScanResult,
)
from qwen3_coder_next.research.schemas import (
    RESEARCH_SCHEMA_VERSION,
    EvidenceItem,
    ResearchNextAction,
    ResearchPacket,
    ResearchRequest,
    ResearchStateStatus,
    SourceHandle,
    SourcePolicy,
    SourceType,
)
from qwen3_coder_next.research.state import ResearchRevision, ResearchState
from qwen3_coder_next.logging import get_logger


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


class _ResearchPipelineObserver:
    """Internal trace builder for deterministic pipeline observability."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._stage_transitions: list[ResearchStageTrace] = []
        self._executed_stage_count = 0
        self._skipped_stage_count = 0

    def stage_started(self, stage_name: str, *, detail: str = "") -> None:
        """Record the start of a stage."""

        self._append_transition(stage_name, "started", detail=detail)
        self._logger.info("Research stage started: stage=%s", stage_name)

    def stage_completed(
        self,
        stage_name: str,
        *,
        source_count: int,
        evidence_count: int,
        detail: str = "",
    ) -> None:
        """Record the successful completion of a stage."""

        self._executed_stage_count += 1
        self._append_transition(
            stage_name,
            "completed",
            source_count=source_count,
            evidence_count=evidence_count,
            detail=detail,
        )
        self._logger.info(
            "Research stage completed: stage=%s source_count=%s evidence_count=%s",
            stage_name,
            source_count,
            evidence_count,
        )

    def stage_skipped(self, stage_name: str, *, detail: str) -> None:
        """Record a skipped stage."""

        self._skipped_stage_count += 1
        self._append_transition(stage_name, "skipped", detail=detail)
        self._logger.info("Research stage skipped: stage=%s reason=%s", stage_name, detail)

    def finalize(
        self,
        *,
        stage_order: tuple[str, ...],
        source_handle_count: int,
        evidence_source_count: int,
        normalized_evidence_count: int,
        packet: ResearchPacket,
        clarification_required: bool,
    ) -> ResearchPipelineObservability:
        """Build the final observability snapshot for the run."""

        failure_record = (
            ResearchFailureRecord(
                stage_name=_PIPELINE_STAGE_PACKET,
                reason="clarification_required",
                fallback_action=packet.recommended_next_action,
                detail=(
                    f"stages={len(stage_order)}|evidence_items={len(packet.evidence)}|"
                    f"confidence={packet.confidence}"
                ),
            )
            if clarification_required
            else None
        )
        metrics = ResearchFlowMetrics(
            executed_stage_count=self._executed_stage_count,
            skipped_stage_count=self._skipped_stage_count,
            source_handle_count=source_handle_count,
            evidence_source_count=evidence_source_count,
            normalized_evidence_count=normalized_evidence_count,
            packet_evidence_count=len(packet.evidence),
            packet_confidence=packet.confidence,
            clarification_required=clarification_required,
        )
        return ResearchPipelineObservability(
            stage_transitions=tuple(self._stage_transitions),
            metrics=metrics,
            fallback_decision=packet.recommended_next_action,
            clarification_required=clarification_required,
            failure_record=failure_record,
        )

    def _append_transition(
        self,
        stage_name: str,
        event: str,
        *,
        source_count: int = 0,
        evidence_count: int = 0,
        detail: str = "",
    ) -> None:
        self._stage_transitions.append(
            ResearchStageTrace(
                stage_name=stage_name,
                event=event,
                sequence_number=len(self._stage_transitions) + 1,
                source_count=source_count,
                evidence_count=evidence_count,
                detail=detail,
            )
        )


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
    observability: ResearchPipelineObservability = field(
        default_factory=ResearchPipelineObservability.empty
    )
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
            "observability": self.observability.to_dict(),
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
        observability = payload.get("observability")
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
            observability=ResearchPipelineObservability.from_dict(dict(observability))
            if observability
            else ResearchPipelineObservability.empty(),
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
    logger: logging.Logger = field(
        default_factory=lambda: get_logger("qwen3_coder_next.research.pipeline"),
        repr=False,
        compare=False,
    )

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
        document_refs_tuple = tuple(document_refs)
        log_artifacts_tuple = tuple(log_artifacts)
        error_artifacts_tuple = tuple(error_artifacts)
        state = research_state or ResearchState(state_id=f"{request.request_id}-research-state")
        state = state.with_request(request).with_source_policy(source_policy)
        observer = _ResearchPipelineObserver(self.logger)
        self.logger.info("Research pipeline started: request_id=%s", request.request_id)

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
            observer.stage_started(_PIPELINE_STAGE_SCAN)
            repository_scan_result = self.repository_scanner.scan(
                repository_root_path,
                request,
                source_policy,
            )
            observer.stage_completed(
                _PIPELINE_STAGE_SCAN,
                source_count=len(repository_scan_result.source_handles),
                evidence_count=len(repository_scan_result.evidence_items),
                detail=f"repository_root={repository_root_path}",
            )
            stage_order.append(_PIPELINE_STAGE_SCAN)
            source_handles.extend(repository_scan_result.source_handles)
            evidence_sources.append(repository_scan_result)
        else:
            observer.stage_skipped(
                _PIPELINE_STAGE_SCAN,
                detail=(
                    "repository_root_not_provided"
                    if repository_root_path is None
                    else "source_policy_disallows_repo_scan"
                ),
            )

        if self._allows_documents(source_policy):
            observer.stage_started(_PIPELINE_STAGE_DOCUMENTS)
            document_fetch_result = self.document_fetcher.fetch(
                request,
                source_policy,
                document_refs_tuple,
                repository_root=repository_root_path,
            )
            observer.stage_completed(
                _PIPELINE_STAGE_DOCUMENTS,
                source_count=len(document_fetch_result.source_handles),
                evidence_count=len(document_fetch_result.evidence_items),
                detail="document_refs=%s" % len(document_refs_tuple),
            )
            stage_order.append(_PIPELINE_STAGE_DOCUMENTS)
            source_handles.extend(document_fetch_result.source_handles)
            if document_fetch_result.evidence_items:
                evidence_sources.append(document_fetch_result)
        else:
            observer.stage_skipped(_PIPELINE_STAGE_DOCUMENTS, detail="source_policy_disallows_docs")

        if self._allows_logs(source_policy):
            observer.stage_started(_PIPELINE_STAGE_LOGS)
            log_fetch_result = self.log_fetcher.fetch(
                request,
                source_policy,
                log_artifacts_tuple,
                repository_root=repository_root_path,
            )
            observer.stage_completed(
                _PIPELINE_STAGE_LOGS,
                source_count=len(log_fetch_result.source_handles),
                evidence_count=len(log_fetch_result.evidence_items),
                detail="log_artifacts=%s" % len(log_artifacts_tuple),
            )
            stage_order.append(_PIPELINE_STAGE_LOGS)
            source_handles.extend(log_fetch_result.source_handles)
            if log_fetch_result.evidence_items:
                evidence_sources.append(log_fetch_result)
        else:
            observer.stage_skipped(_PIPELINE_STAGE_LOGS, detail="source_policy_disallows_logs")

        if self._allows_errors(source_policy):
            observer.stage_started(_PIPELINE_STAGE_ERRORS)
            error_fetch_result = self.error_fetcher.fetch(
                request,
                source_policy,
                error_artifacts_tuple,
            )
            observer.stage_completed(
                _PIPELINE_STAGE_ERRORS,
                source_count=len(error_fetch_result.source_handles),
                evidence_count=len(error_fetch_result.evidence_items),
                detail="error_artifacts=%s" % len(error_artifacts_tuple),
            )
            stage_order.append(_PIPELINE_STAGE_ERRORS)
            source_handles.extend(error_fetch_result.source_handles)
            if error_fetch_result.evidence_items:
                evidence_sources.append(error_fetch_result)
        else:
            observer.stage_skipped(_PIPELINE_STAGE_ERRORS, detail="source_policy_disallows_errors")

        observer.stage_started(_PIPELINE_STAGE_NORMALIZE)
        evidence_normalization_result = self.evidence_normalizer.normalize(
            tuple(evidence_sources),
            request=request,
            source_policy=source_policy,
        )
        observer.stage_completed(
            _PIPELINE_STAGE_NORMALIZE,
            source_count=len(evidence_sources),
            evidence_count=len(evidence_normalization_result.evidence_items),
            detail="normalized_evidence=%s" % len(evidence_normalization_result.evidence_items),
        )
        stage_order.append(_PIPELINE_STAGE_NORMALIZE)

        observer.stage_started(_PIPELINE_STAGE_PACKET)
        research_packet = self.packet_assembler.assemble(
            request,
            evidence_normalization_result,
            source_policy=source_policy,
        )
        observer.stage_completed(
            _PIPELINE_STAGE_PACKET,
            source_count=len(research_packet.evidence),
            evidence_count=len(research_packet.evidence),
            detail=f"next_action={research_packet.recommended_next_action.value}",
        )
        stage_order.append(_PIPELINE_STAGE_PACKET)

        state = state.with_selected_sources(tuple(source_handles))
        for evidence_item in evidence_normalization_result.evidence_items:
            state = state.add_evidence_item(evidence_item)
        clarification_required = self._determine_clarification_required(
            research_packet,
            evidence_normalization_result,
            source_policy,
            repository_root_path,
        )
        if clarification_required:
            state = state.with_research_packet(research_packet).with_status(
                ResearchStateStatus.NEEDS_CLARIFICATION
            )
        else:
            state = state.with_research_packet(research_packet)

        observability = observer.finalize(
            stage_order=tuple(stage_order),
            source_handle_count=len(source_handles),
            evidence_source_count=len(evidence_sources),
            normalized_evidence_count=len(evidence_normalization_result.evidence_items),
            packet=research_packet,
            clarification_required=clarification_required,
        )
        if clarification_required:
            self.logger.warning(
                "Research clarification required: request_id=%s fallback=%s evidence_count=%s confidence=%s",
                request.request_id,
                observability.fallback_decision.value,
                len(research_packet.evidence),
                research_packet.confidence,
            )
        self.logger.info(
            "Research pipeline finished: request_id=%s stages=%s evidence_items=%s",
            request.request_id,
            len(stage_order),
            len(research_packet.evidence),
        )

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
            observability=observability,
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

    def _determine_clarification_required(
        self,
        research_packet: ResearchPacket,
        evidence_normalization_result: ResearchEvidenceNormalizationResult,
        source_policy: SourcePolicy,
        repository_root: Path | None,
    ) -> bool:
        """Return whether the current run should surface a clarification path."""

        unsupported_sources = not any(
            (
                (repository_root is not None and SourceType.REPO_FILE in source_policy.allowed_sources),
                SourceType.DOC in source_policy.allowed_sources,
                SourceType.LOG in source_policy.allowed_sources,
                SourceType.ERROR_ARTIFACT in source_policy.allowed_sources,
            )
        )
        insufficient_evidence = (
            research_packet.recommended_next_action != ResearchNextAction.CODE
            or not evidence_normalization_result.evidence_items
        )
        return unsupported_sources or insufficient_evidence


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
