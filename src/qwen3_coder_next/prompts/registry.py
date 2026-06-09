"""In-memory prompt registry."""

from collections.abc import Iterable

from qwen3_coder_next.prompts.contracts import PromptTemplate


class PromptRegistry:
    """Store and retrieve prompt templates by name and version."""

    def __init__(self) -> None:
        self._templates: dict[tuple[str, str], PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> PromptTemplate:
        """Register a prompt template and return it."""

        self._templates[(template.name, template.version)] = template
        return template

    def get(self, name: str, version: str) -> PromptTemplate:
        """Retrieve a registered prompt template."""

        return self._templates[(name, version)]

    def list(self) -> list[PromptTemplate]:
        """Return all registered templates in insertion order."""

        return list(self._templates.values())

    def extend(self, templates: Iterable[PromptTemplate]) -> None:
        """Register multiple templates."""

        for template in templates:
            self.register(template)
