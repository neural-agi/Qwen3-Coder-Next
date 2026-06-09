"""Prompt loading utilities."""

from pathlib import Path

from qwen3_coder_next.prompts.contracts import PromptLoadRequest, PromptLoadResult, PromptTemplate
from qwen3_coder_next.prompts.registry import PromptRegistry


class PromptLoader:
    """Load versioned prompt templates from a filesystem directory."""

    def __init__(self, base_path: Path, registry: PromptRegistry | None = None) -> None:
        self._base_path = base_path
        self._registry = registry or PromptRegistry()

    @property
    def registry(self) -> PromptRegistry:
        """Return the associated registry."""

        return self._registry

    def load(self, request: PromptLoadRequest) -> PromptLoadResult:
        """Load a prompt template by name and version."""

        path = self._template_path(request.name, request.version)
        content = path.read_text(encoding="utf-8")
        template = PromptTemplate(
            name=request.name,
            version=request.version,
            content=content,
        )
        self._registry.register(template)
        return PromptLoadResult(template=template, source_path=str(path))

    def load_all(self) -> list[PromptTemplate]:
        """Load every versioned prompt template found in the base directory."""

        templates: list[PromptTemplate] = []
        if not self._base_path.exists():
            return templates

        for path in sorted(self._base_path.glob("*__*.txt")):
            name, version = self._parse_stem(path.stem)
            template = PromptTemplate(
                name=name,
                version=version,
                content=path.read_text(encoding="utf-8"),
            )
            self._registry.register(template)
            templates.append(template)
        return templates

    def _template_path(self, name: str, version: str) -> Path:
        return self._base_path / f"{name}__{version}.txt"

    def _parse_stem(self, stem: str) -> tuple[str, str]:
        name, version = stem.rsplit("__", 1)
        return name, version
