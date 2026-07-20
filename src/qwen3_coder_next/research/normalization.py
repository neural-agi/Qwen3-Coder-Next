"""Deterministic research request normalization and source policy shaping."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid5

from qwen3_coder_next.research.schemas import (
    RESEARCH_SCHEMA_VERSION,
    ResearchBudget,
    ResearchRequest,
    ResearchTaskType,
    SourcePolicy,
    SourceType,
    _default_source_policy,
)


class ResearchNormalizationError(ValueError):
    """Base error for research normalization failures."""


class MalformedResearchRequestError(ResearchNormalizationError):
    """Raised when a raw research request cannot be normalized."""


class MalformedSourcePolicyError(ResearchNormalizationError):
    """Raised when a source policy payload cannot be normalized."""


@dataclass(frozen=True, slots=True)
class ResearchNormalizationResult:
    """Structured result returned by the research request normalizer."""

    request: ResearchRequest
    source_policy: SourcePolicy
    normalized_at: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0, UTC)
    )
    schema_version: int = RESEARCH_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the normalization result into a deterministic mapping."""

        return {
            "request": self.request.to_dict(),
            "source_policy": self.source_policy.to_dict(),
            "normalized_at": self.normalized_at.isoformat(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResearchNormalizationResult":
        """Rehydrate a normalization result from serialized data."""

        return cls(
            request=ResearchRequest.from_dict(dict(payload["request"])),
            source_policy=SourcePolicy.from_dict(dict(payload["source_policy"])),
            normalized_at=datetime.fromisoformat(
                str(
                    payload.get(
                        "normalized_at",
                        datetime.fromtimestamp(0, UTC).isoformat(),
                    )
                )
            ),
            schema_version=int(payload.get("schema_version", RESEARCH_SCHEMA_VERSION)),
        )


class ResearchRequestNormalizer:
    """Normalize raw research requests into canonical research contracts."""

    def normalize(
        self,
        request: str | Mapping[str, Any],
        *,
        request_id: str | None = None,
        task_type: ResearchTaskType | str | None = None,
        target_repo: str | None = None,
        query_text: str | None = None,
        constraints: tuple[str, ...] | list[str] | None = None,
        hints: tuple[str, ...] | list[str] | None = None,
        budget: ResearchBudget | Mapping[str, Any] | None = None,
        source_policy: SourcePolicy | Mapping[str, Any] | None = None,
    ) -> ResearchNormalizationResult:
        """Normalize raw input into a canonical research request."""

        parsed = self._parse_request(request)
        resolved_task_type = self._normalize_task_type(
            task_type if task_type is not None else parsed["task_type"]
        )
        resolved_target_repo = self._normalize_text(
            target_repo if target_repo is not None else parsed["target_repo"]
        )
        resolved_query_text = self._normalize_text(
            query_text if query_text is not None else parsed["query_text"]
        )
        if not resolved_query_text:
            raise MalformedResearchRequestError("Research request query_text must not be empty.")

        resolved_constraints = self._normalize_sequence(
            constraints if constraints is not None else parsed["constraints"]
        )
        resolved_hints = self._normalize_sequence(hints if hints is not None else parsed["hints"])
        resolved_budget = self._normalize_budget(
            budget if budget is not None else parsed["budget"]
        )
        resolved_source_policy = self._normalize_source_policy(
            source_policy if source_policy is not None else parsed["source_policy"]
        )
        resolved_request_id = self._normalize_request_id(
            request_id or parsed["request_id"],
            resolved_task_type,
            resolved_target_repo,
            resolved_query_text,
            resolved_constraints,
            resolved_hints,
            resolved_budget,
            resolved_source_policy,
        )

        research_request = ResearchRequest(
            request_id=resolved_request_id,
            task_type=resolved_task_type,
            target_repo=resolved_target_repo,
            query_text=resolved_query_text,
            constraints=resolved_constraints,
            hints=resolved_hints,
            budget=resolved_budget,
        )
        return ResearchNormalizationResult(
            request=research_request,
            source_policy=resolved_source_policy,
        )

    def _parse_request(self, request: str | Mapping[str, Any]) -> dict[str, Any]:
        """Parse raw request input into normalized components."""

        if isinstance(request, str):
            query_text = self._normalize_text(request)
            if not query_text:
                raise MalformedResearchRequestError("Research request text must not be empty.")
            return {
                "request_id": None,
                "task_type": ResearchTaskType.INVESTIGATION,
                "target_repo": "",
                "query_text": query_text,
                "constraints": (),
                "hints": (),
                "budget": ResearchBudget(),
                "source_policy": None,
            }

        if not isinstance(request, Mapping):
            raise MalformedResearchRequestError("Research request must be a string or mapping.")

        query_text = self._normalize_text(
            str(
                request.get("query_text")
                or request.get("query")
                or request.get("task")
                or request.get("raw_text")
                or ""
            )
        )
        if not query_text:
            raise MalformedResearchRequestError(
                "Research request must include query_text, query, task, or raw_text."
            )

        return {
            "request_id": request.get("request_id"),
            "task_type": request.get("task_type") or ResearchTaskType.INVESTIGATION,
            "target_repo": request.get("target_repo") or "",
            "query_text": query_text,
            "constraints": self._normalize_sequence(request.get("constraints", ())),
            "hints": self._normalize_sequence(request.get("hints", ())),
            "budget": request.get("budget") or ResearchBudget(),
            "source_policy": request.get("source_policy"),
        }

    def _normalize_request_id(
        self,
        request_id: str | None,
        task_type: ResearchTaskType,
        target_repo: str,
        query_text: str,
        constraints: tuple[str, ...],
        hints: tuple[str, ...],
        budget: ResearchBudget,
        source_policy: SourcePolicy,
    ) -> str:
        """Normalize or derive a stable research request identifier."""

        if request_id:
            normalized = self._normalize_text(request_id)
            if normalized:
                return normalized

        canonical_source = {
            "task_type": task_type.value,
            "target_repo": target_repo,
            "query_text": query_text,
            "constraints": list(constraints),
            "hints": list(hints),
            "budget": budget.to_dict(),
            "source_policy": source_policy.to_dict(),
        }
        canonical_json = json.dumps(
            canonical_source,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        digest = sha256(canonical_json.encode("utf-8")).hexdigest()
        return f"research-{uuid5(NAMESPACE_URL, digest)}"

    def _normalize_task_type(self, value: ResearchTaskType | str | None) -> ResearchTaskType:
        """Normalize task type values into the canonical enum."""

        if value is None:
            return ResearchTaskType.INVESTIGATION
        if isinstance(value, ResearchTaskType):
            return value
        normalized = self._normalize_text(value)
        if not normalized:
            return ResearchTaskType.INVESTIGATION
        try:
            return ResearchTaskType(normalized)
        except ValueError as exc:
            raise MalformedResearchRequestError(
                f"Unsupported research task_type: {normalized!r}"
            ) from exc

    def _normalize_budget(self, value: ResearchBudget | Mapping[str, Any]) -> ResearchBudget:
        """Normalize a budget payload into a canonical budget object."""

        if isinstance(value, ResearchBudget):
            return value
        if not isinstance(value, Mapping):
            raise MalformedResearchRequestError("Research budget must be a mapping or ResearchBudget.")
        return ResearchBudget.from_dict(dict(value))

    def _normalize_source_policy(
        self, value: SourcePolicy | Mapping[str, Any] | None
    ) -> SourcePolicy:
        """Normalize a source policy payload into a canonical policy object."""

        if value is None:
            return _default_source_policy()
        if isinstance(value, SourcePolicy):
            return value
        if not isinstance(value, Mapping):
            raise MalformedSourcePolicyError(
                "Source policy must be a mapping, SourcePolicy, or omitted."
            )

        allowed_sources = self._normalize_source_types(value.get("allowed_sources", ()))
        preferred_sources = self._normalize_source_types(value.get("preferred_sources", ()))
        blocked_sources = self._normalize_source_types(value.get("blocked_sources", ()))
        if blocked_sources and any(item in allowed_sources for item in blocked_sources):
            raise MalformedSourcePolicyError(
                "Blocked sources cannot also appear in allowed sources."
            )
        weights_raw = value.get("source_rank_weights", {})
        if not isinstance(weights_raw, Mapping):
            raise MalformedSourcePolicyError("source_rank_weights must be a mapping.")

        return SourcePolicy(
            allowed_sources=allowed_sources,
            preferred_sources=preferred_sources,
            blocked_sources=blocked_sources,
            source_rank_weights={
                str(key): float(weights_raw[key]) for key in sorted(weights_raw, key=lambda item: str(item))
            },
            max_evidence_items=int(value.get("max_evidence_items", 20)),
            max_snippet_chars=int(value.get("max_snippet_chars", 1_200)),
            cache_ttl_minutes=int(value.get("cache_ttl_minutes", 60)),
        )

    def _normalize_source_types(self, value: Any) -> tuple[SourceType, ...]:
        """Normalize source type values into a deterministic tuple."""

        if value is None:
            return ()
        if isinstance(value, (str, bytes)):
            normalized = self._normalize_text(value)
            if not normalized:
                return ()
            return (SourceType(normalized),)
        if not isinstance(value, (list, tuple, set)):
            raise MalformedSourcePolicyError("Source type fields must be iterables of strings.")
        normalized_items: list[SourceType] = []
        seen: set[SourceType] = set()
        for item in value:
            source_type = self._coerce_source_type(item)
            if source_type not in seen:
                normalized_items.append(source_type)
                seen.add(source_type)
        return tuple(normalized_items)

    def _coerce_source_type(self, value: Any) -> SourceType:
        """Normalize a single source type and wrap enum errors consistently."""

        normalized = self._normalize_text(value)
        if not normalized:
            raise MalformedSourcePolicyError("Source type values must not be empty.")
        try:
            return SourceType(normalized)
        except ValueError as exc:
            raise MalformedSourcePolicyError(
                f"Unsupported source type: {normalized!r}"
            ) from exc

    def _normalize_sequence(self, value: Any) -> tuple[str, ...]:
        """Normalize a sequence into a deterministic tuple of strings."""

        if value is None:
            return ()
        if isinstance(value, (str, bytes)):
            normalized = self._normalize_text(value)
            return (normalized,) if normalized else ()
        if not isinstance(value, (list, tuple, set)):
            raise MalformedResearchRequestError("Sequence fields must be iterable strings.")
        normalized_items: list[str] = []
        seen: set[str] = set()
        for item in value:
            normalized = self._normalize_text(item)
            if normalized and normalized not in seen:
                normalized_items.append(normalized)
                seen.add(normalized)
        return tuple(normalized_items)

    def _normalize_text(self, value: Any) -> str:
        """Collapse text to a canonical single-spaced form."""

        return " ".join(str(value).strip().split())


def normalize_research_request(
    request: str | Mapping[str, Any],
    *,
    request_id: str | None = None,
    task_type: ResearchTaskType | str | None = None,
    target_repo: str | None = None,
    query_text: str | None = None,
    constraints: tuple[str, ...] | list[str] | None = None,
    hints: tuple[str, ...] | list[str] | None = None,
    budget: ResearchBudget | Mapping[str, Any] | None = None,
    source_policy: SourcePolicy | Mapping[str, Any] | None = None,
) -> ResearchNormalizationResult:
    """Normalize a raw research request using the default normalizer."""

    return ResearchRequestNormalizer().normalize(
        request,
        request_id=request_id,
        task_type=task_type,
        target_repo=target_repo,
        query_text=query_text,
        constraints=constraints,
        hints=hints,
        budget=budget,
        source_policy=source_policy,
    )
