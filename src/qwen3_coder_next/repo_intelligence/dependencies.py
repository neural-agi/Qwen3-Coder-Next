"""Shallow, evidence-backed dependency hint extraction for Part 9 Step 4."""
from __future__ import annotations

import re
from pathlib import Path

from qwen3_coder_next.repo_intelligence.schemas import DependencyHint, FileRecord

_PATTERNS = {
    "python": re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))"),
    "javascript": re.compile(r"(?:import\s+(?:[^\"']+\s+from\s+)?|require\s*\()\s*[\"']([^\"']+)[\"']"),
    "typescript": re.compile(r"(?:import\s+(?:[^\"']+\s+from\s+)?|require\s*\()\s*[\"']([^\"']+)[\"']"),
    "c": re.compile(r'^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]'),
    "cpp": re.compile(r'^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]'),
    "java": re.compile(r"^\s*import\s+([\w.]+)") ,
    "go": re.compile(r'^\s*import\s+\"([^\"]+)\"'),
    "rust": re.compile(r"^\s*use\s+([\w:]+)"),
    "ruby": re.compile(r"^\s*require\s+[\"']([^\"']+)[\"']"),
    "php": re.compile(r"(?:require|include)(?:_once)?\s*\(?\s*[\"']([^\"']+)[\"']"),
}


class DependencyHintExtractor:
    """Extract first-order textual import/include hints without resolving them."""

    def extract(self, record: FileRecord, repository_root: str | Path) -> tuple[DependencyHint, ...]:
        if not isinstance(record, FileRecord):
            raise ValueError("record must be a FileRecord.")
        root = Path(repository_root)
        if not root.exists() or not root.is_dir():
            raise ValueError("repository_root must be an existing directory.")
        if record.language not in _PATTERNS:
            return ()
        path = (root.resolve() / Path(record.path)).resolve()
        try:
            path.relative_to(root.resolve())
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError, ValueError):
            return ()
        pattern = _PATTERNS[record.language]
        hints: list[DependencyHint] = []
        seen: set[tuple[str, str]] = set()
        for line_number, line in enumerate(lines, start=1):
            match = pattern.search(line)
            if not match:
                continue
            target = next((value for value in match.groups() if value), "").strip()
            key = (target, line)
            if not target or key in seen:
                continue
            seen.add(key)
            hints.append(DependencyHint(record.normalized_path, target, "import", 0.5, f"line {line_number}: {line.strip()}"))
        return tuple(sorted(hints, key=lambda item: (item.target_path, item.evidence)))

    def extract_many(self, records: tuple[FileRecord, ...], repository_root: str | Path) -> tuple[DependencyHint, ...]:
        if isinstance(records, (str, bytes)):
            raise ValueError("records must be a collection of FileRecord values.")
        try:
            values = tuple(records)
        except TypeError as exc:
            raise ValueError("records must be a collection of FileRecord values.") from exc
        hints = [hint for record in values for hint in self.extract(record, repository_root)]
        return tuple(sorted(hints, key=lambda item: (item.source_path, item.target_path, item.evidence)))
