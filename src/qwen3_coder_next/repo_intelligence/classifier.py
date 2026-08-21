"""Deterministic shallow file classification for Part 9 Step 3."""
from __future__ import annotations

from dataclasses import replace
from pathlib import PurePosixPath

from qwen3_coder_next.repo_intelligence.schemas import FileRecord

_LANGUAGES = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".jsx": "javascript", ".tsx": "typescript",
    ".java": "java", ".go": "go", ".rs": "rust", ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin", ".kts": "kotlin",
    ".sh": "shell", ".ps1": "powershell", ".sql": "sql", ".html": "html", ".css": "css", ".scss": "scss",
}
_DOCUMENT_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
_DATA_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".tsv"}
_CONFIG_NAMES = {".env", ".gitignore", ".dockerignore", "dockerfile", "makefile", "pyproject.toml", "package.json"}
_BUILD_NAMES = {"makefile", "build.gradle", "pom.xml", "cargo.toml", "webpack.config.js", "vite.config.js"}


class FileClassifier:
    """Classify one scanner-produced FileRecord without reading or mutating files."""

    def classify(self, record: FileRecord) -> FileRecord:
        if not isinstance(record, FileRecord):
            raise ValueError("record must be a FileRecord.")
        path = PurePosixPath(record.normalized_path)
        name = path.name.lower()
        extension = path.suffix.lower()
        parts = {part.lower() for part in path.parts}
        language = _LANGUAGES.get(extension, "unknown")
        file_type = "unknown"
        if "generated" in parts or name.endswith((".generated", ".min.js", ".min.css", ".g.cs")):
            file_type = "generated"
        elif "test" in parts or "tests" in parts or name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".spec.ts")):
            file_type = "test"
        elif name in _BUILD_NAMES or "build" in parts or "dist" in parts:
            file_type = "build"
        elif name in _CONFIG_NAMES or extension in {".ini", ".cfg", ".conf"}:
            file_type = "configuration"
        elif extension in _DOCUMENT_EXTENSIONS:
            file_type = "documentation"
        elif extension in _DATA_EXTENSIONS:
            file_type = "data"
        elif language != "unknown":
            file_type = "source"
        return replace(record, file_type=file_type, language=language)

    def classify_many(self, records: tuple[FileRecord, ...]) -> tuple[FileRecord, ...]:
        if isinstance(records, (str, bytes)):
            raise ValueError("records must be a collection of FileRecord values.")
        try:
            values = tuple(records)
        except TypeError as exc:
            raise ValueError("records must be a collection of FileRecord values.") from exc
        classified = tuple(self.classify(record) for record in values)
        return tuple(sorted(classified, key=lambda item: item.normalized_path))
