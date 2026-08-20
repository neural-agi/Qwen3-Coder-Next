"""Deterministic evaluation audit persistence."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from qwen3_coder_next.evaluation.schemas import EvaluationDecision

class EvaluationAuditStore:
    def __init__(self, path: Path) -> None: self._path = Path(path)
    def append(self, decision: EvaluationDecision, *, timestamp: str) -> None:
        if not isinstance(decision, EvaluationDecision) or not timestamp: raise ValueError("decision and timestamp are required.")
        records = self.records(); records.append({"timestamp":timestamp, **decision.to_dict()}); self._path.parent.mkdir(parents=True, exist_ok=True); self._path.write_text(json.dumps(records, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    def records(self) -> list[dict[str, Any]]:
        if not self._path.exists(): return []
        data = json.loads(self._path.read_text(encoding="utf-8"));
        if not isinstance(data, list): raise ValueError("audit payload must be a list.")
        return list(data)
