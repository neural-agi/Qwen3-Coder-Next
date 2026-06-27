"""Deterministic request normalization for the planning layer."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid5

from qwen3_coder_next.planning.schemas import PLANNER_SCHEMA_VERSION, PlannerRequest


class PlanningNormalizationError(ValueError):
    """Base error for planning normalization failures."""


class MalformedPlannerRequestError(PlanningNormalizationError):
    """Raised when a raw planning request cannot be normalized."""


@dataclass(frozen=True, slots=True)
class PlannerNormalizationResult:
    """Structured result returned by the request normalizer."""

    request: PlannerRequest
    metadata: dict[str, Any] = field(default_factory=dict)
    normalized_at: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0, UTC)
    )
    schema_version: int = PLANNER_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Serialize the normalization result into a deterministic mapping."""

        return {
            "request": self.request.to_dict(),
            "metadata": dict(self.metadata),
            "normalized_at": self.normalized_at.isoformat(),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PlannerNormalizationResult":
        """Rehydrate a normalization result from serialized data."""

        return cls(
            request=PlannerRequest.from_dict(dict(payload["request"])),
            metadata=dict(payload.get("metadata", {})),
            normalized_at=datetime.fromisoformat(
                str(
                    payload.get(
                        "normalized_at",
                        datetime.fromtimestamp(0, UTC).isoformat(),
                    )
                )
            ),
            schema_version=int(payload.get("schema_version", PLANNER_SCHEMA_VERSION)),
        )


class PlannerRequestNormalizer:
    """Normalize raw planning requests into canonical planner contracts."""

    def normalize(
        self,
        request: str | Mapping[str, Any],
        *,
        task_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        constraints: tuple[str, ...] | list[str] | None = None,
        source_context: tuple[str, ...] | list[str] | None = None,
        environment: Mapping[str, Any] | None = None,
    ) -> PlannerNormalizationResult:
        """Normalize raw input into a canonical planner request."""

        normalized_goal, derived_task_id, request_metadata, request_constraints, request_source_context, request_environment = (
            self._parse_request(request)
        )
        resolved_task_id = self._normalize_task_id(task_id or derived_task_id, normalized_goal, request_constraints, request_source_context, request_environment)
        resolved_metadata = self._normalize_mapping(metadata if metadata is not None else request_metadata)
        resolved_constraints = self._normalize_sequence(
            constraints if constraints is not None else request_constraints
        )
        resolved_source_context = self._normalize_sequence(
            source_context if source_context is not None else request_source_context
        )
        resolved_environment = self._normalize_mapping(
            environment if environment is not None else request_environment
        )

        planner_request = PlannerRequest(
            task_id=resolved_task_id,
            user_goal=normalized_goal,
            constraints=resolved_constraints,
            environment=resolved_environment,
            source_context=resolved_source_context,
        )
        return PlannerNormalizationResult(
            request=planner_request,
            metadata=resolved_metadata,
        )

    def _parse_request(
        self, request: str | Mapping[str, Any]
    ) -> tuple[str, str | None, dict[str, Any], tuple[str, ...], tuple[str, ...], dict[str, Any]]:
        """Parse raw request input into normalized components."""

        if isinstance(request, str):
            normalized_goal = self._normalize_text(request)
            if not normalized_goal:
                raise MalformedPlannerRequestError("Planning request text must not be empty.")
            return normalized_goal, None, {}, (), (), {}

        if not isinstance(request, Mapping):
            raise MalformedPlannerRequestError("Planning request must be a string or mapping.")

        normalized_goal = self._normalize_text(
            str(request.get("user_goal") or request.get("raw_text") or request.get("text") or "")
        )
        if not normalized_goal:
            raise MalformedPlannerRequestError("Planning request must include user_goal or raw_text.")

        derived_task_id = request.get("task_id")
        metadata = dict(request.get("metadata", {}))
        constraints = self._normalize_sequence(request.get("constraints", ()))
        source_context = self._normalize_sequence(request.get("source_context", ()))
        environment = self._normalize_mapping(request.get("environment", {}))
        return (
            normalized_goal,
            str(derived_task_id).strip() if derived_task_id is not None else None,
            metadata,
            constraints,
            source_context,
            environment,
        )

    def _normalize_task_id(
        self,
        task_id: str | None,
        user_goal: str,
        constraints: tuple[str, ...],
        source_context: tuple[str, ...],
        environment: dict[str, Any],
    ) -> str:
        """Normalize or derive a stable task identifier."""

        if task_id:
            normalized = self._normalize_text(task_id)
            if normalized:
                return normalized

        canonical_source = {
            "user_goal": user_goal,
            "constraints": list(constraints),
            "source_context": list(source_context),
            "environment": environment,
        }
        canonical_json = json.dumps(
            canonical_source,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        digest = sha256(canonical_json.encode("utf-8")).hexdigest()
        return f"task-{uuid5(NAMESPACE_URL, digest)}"

    def _normalize_text(self, value: Any) -> str:
        """Collapse text to a canonical single-spaced form."""

        return " ".join(str(value).strip().split())

    def _normalize_sequence(self, value: Any) -> tuple[str, ...]:
        """Normalize a sequence into a deterministic tuple of strings."""

        if value is None:
            return ()
        if isinstance(value, (str, bytes)):
            normalized = self._normalize_text(value)
            return (normalized,) if normalized else ()
        if not isinstance(value, (list, tuple, set)):
            raise MalformedPlannerRequestError("Sequence fields must be iterable strings.")
        normalized_items = []
        for item in value:
            normalized = self._normalize_text(item)
            if normalized:
                normalized_items.append(normalized)
        return tuple(normalized_items)

    def _normalize_mapping(self, value: Any) -> dict[str, Any]:
        """Normalize a mapping into a deterministic, string-keyed dictionary."""

        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise MalformedPlannerRequestError("Mapping fields must be mappings.")
        normalized: dict[str, Any] = {}
        for key in sorted(value.keys(), key=lambda item: str(item)):
            normalized[str(key)] = self._normalize_value(value[key])
        return normalized

    def _normalize_value(self, value: Any) -> Any:
        """Normalize an arbitrary metadata value recursively."""

        if isinstance(value, Mapping):
            return self._normalize_mapping(value)
        if isinstance(value, (list, tuple, set)):
            return tuple(self._normalize_value(item) for item in value)
        if isinstance(value, str):
            return self._normalize_text(value)
        return value


def normalize_planner_request(
    request: str | Mapping[str, Any],
    *,
    task_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    constraints: tuple[str, ...] | list[str] | None = None,
    source_context: tuple[str, ...] | list[str] | None = None,
    environment: Mapping[str, Any] | None = None,
) -> PlannerNormalizationResult:
    """Normalize a raw planning request using the default normalizer."""

    return PlannerRequestNormalizer().normalize(
        request,
        task_id=task_id,
        metadata=metadata,
        constraints=constraints,
        source_context=source_context,
        environment=environment,
    )
