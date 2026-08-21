"""Deterministic, read-only repository discovery for Part 9 Step 2."""
from __future__ import annotations

import fnmatch
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from qwen3_coder_next.repo_intelligence.schemas import FileRecord, FolderRecord, REPOSITORY_SCHEMA_VERSION

DEFAULT_IGNORED_DIRECTORIES = (".git", ".hg", ".svn", "__pycache__", ".venv", "node_modules", "build", "dist", "vendor")


@dataclass(frozen=True, slots=True)
class RepositoryScanResult:
    """Immutable raw repository inventory produced by ``RepositoryScanner``."""

    root_path: str
    files: tuple[FileRecord, ...]
    folders: tuple[FolderRecord, ...]
    ignored_paths: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    schema_version: int = REPOSITORY_SCHEMA_VERSION


class RepositoryScanner:
    """Walk a repository without mutating it or performing later classification work."""

    def __init__(self, ignored_directories: Iterable[str] = DEFAULT_IGNORED_DIRECTORIES) -> None:
        if isinstance(ignored_directories, (str, bytes)):
            raise ValueError("ignored_directories must be a collection of names.")
        self._ignored_directories = tuple(self._validate_pattern(item, "ignored directory") for item in ignored_directories)

    @staticmethod
    def _validate_pattern(value: object, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must be non-empty text.")
        return value.strip().replace("\\", "/")

    @staticmethod
    def _relative(root: Path, path: Path) -> str:
        return path.relative_to(root).as_posix()

    def _ignored(self, relative_path: str, *, is_directory: bool) -> bool:
        parts = relative_path.split("/")
        candidates = parts if is_directory else parts[:-1]
        name = parts[-1]
        for pattern in self._ignored_directories:
            if any(fnmatch.fnmatch(part, pattern) or fnmatch.fnmatch("/".join(parts[:index + 1]), pattern) for index, part in enumerate(candidates)):
                return True
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(relative_path, pattern):
                return True
        return False

    def scan(self, repository_root: str | Path) -> RepositoryScanResult:
        root = Path(repository_root)
        if not root.exists() or not root.is_dir():
            raise ValueError("repository_root must be an existing directory.")
        root = root.resolve()
        files: list[FileRecord] = []
        folders: list[FolderRecord] = []
        ignored: list[str] = []
        warnings: list[str] = []
        for current, directory_names, file_names in __import__("os").walk(root, topdown=True, followlinks=False):
            current_path = Path(current)
            kept_directories: list[str] = []
            for name in sorted(directory_names):
                candidate = current_path / name
                relative = self._relative(root, candidate)
                if candidate.is_symlink() or self._ignored(relative, is_directory=True):
                    ignored.append(relative)
                else:
                    kept_directories.append(name)
            directory_names[:] = kept_directories
            if current_path != root:
                relative = self._relative(root, current_path)
                folders.append(FolderRecord(relative, 0, 0))
            for name in sorted(file_names):
                candidate = current_path / name
                relative = self._relative(root, candidate)
                if candidate.is_symlink() or self._ignored(relative, is_directory=False):
                    ignored.append(relative)
                    continue
                try:
                    data = candidate.read_bytes()
                    size = candidate.stat().st_size
                except (OSError, PermissionError) as exc:
                    warnings.append(f"Unreadable file skipped: {relative} ({type(exc).__name__})")
                    continue
                digest = hashlib.sha256(data).hexdigest()
                files.append(FileRecord(relative, relative, "unknown", "unknown", size, digest))
        files.sort(key=lambda item: item.normalized_path)
        ignored.sort()
        warnings.sort()
        folder_counts = {folder.path: [0, 0] for folder in folders}
        for record in files:
            parent = Path(record.normalized_path).parent.as_posix()
            while parent != ".":
                if parent in folder_counts:
                    folder_counts[parent][0] += 1
                parent = Path(parent).parent.as_posix()
        for folder in folders:
            child_folder_count = sum(1 for candidate in folder_counts if Path(candidate).parent.as_posix() == folder.path)
            folder_counts[folder.path][1] = child_folder_count
        folders = [FolderRecord(folder.path, *folder_counts[folder.path]) for folder in sorted(folders, key=lambda item: item.path)]
        return RepositoryScanResult(root.as_posix(), tuple(files), tuple(folders), tuple(ignored), tuple(warnings))
