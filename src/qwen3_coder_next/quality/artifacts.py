"""Immutable quality evidence publication."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qwen3_coder_next.quality.schemas import ReviewFinding, ReviewReport, TestReport


class QualityReportSerializer:
    """Canonical JSON serializer for quality reports."""

    def serialize(self, report: TestReport | ReviewReport) -> str:
        if not isinstance(report, (TestReport, ReviewReport)):
            raise ValueError("report must be a TestReport or ReviewReport instance.")
        return json.dumps(report.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    def deserialize_test_report(self, payload: str | dict[str, Any]) -> TestReport:
        data = json.loads(payload) if isinstance(payload, str) else payload
        if not isinstance(data, dict):
            raise ValueError("serialized report must decode to a mapping.")
        return TestReport(
            task_id=data["task_id"], worktree_id=data["worktree_id"], suite_name=data["suite_name"],
            exit_code=data["exit_code"], status=data["status"], summary=data["summary"],
            failed_cases=tuple(data.get("failed_cases", ())), logs_ref=data.get("logs_ref", ""),
            artifacts_ref=data.get("artifacts_ref", ""),
        )


class QualityArtifactPublisher:
    """Write deterministic, versioned JSON evidence without overwriting artifacts."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def publish(self, task_id: str, name: str, payload: dict[str, Any]) -> str:
        if not isinstance(task_id, str) or not task_id.strip() or not isinstance(name, str) or not name.strip():
            raise ValueError("task_id and name must be non-empty strings.")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping.")
        base = self._root / task_id / name
        version = 1
        path = base.with_suffix(".v1.json")
        while path.exists():
            version += 1
            path = base.with_suffix(f".v{version}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True), encoding="utf-8")
        return str(path.relative_to(self._root))
