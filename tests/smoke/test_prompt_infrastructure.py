"""Smoke tests for the prompt infrastructure."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.prompts import (
    PromptLoadRequest,
    PromptLoader,
    PromptRegistry,
    PromptTemplate,
)


class PromptInfrastructureSmokeTest(unittest.TestCase):
    """Verify prompt contracts, registry, and filesystem loading."""

    def test_prompt_registry_can_register_and_retrieve_templates(self) -> None:
        """Register a versioned template and retrieve it."""

        registry = PromptRegistry()
        template = PromptTemplate(
            name="planning-summary",
            version="v1",
            content="Summarize the plan.",
        )

        registry.register(template)

        self.assertEqual(registry.get("planning-summary", "v1"), template)
        self.assertEqual(registry.list(), [template])

    def test_prompt_loader_loads_versioned_templates(self) -> None:
        """Load a prompt template from a versioned filesystem path."""

        with TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            prompt_path = base_path / "execution-preamble__v1.txt"
            prompt_path.write_text("Prepare the execution context.", encoding="utf-8")

            loader = PromptLoader(base_path)
            result = loader.load(PromptLoadRequest(name="execution-preamble", version="v1"))

            self.assertEqual(result.template.name, "execution-preamble")
            self.assertEqual(result.template.version, "v1")
            self.assertEqual(result.template.content, "Prepare the execution context.")
            self.assertEqual(result.source_path, str(prompt_path))

    def test_prompt_loader_loads_all_versioned_templates(self) -> None:
        """Load all versioned templates from a directory."""

        with TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            (base_path / "one__v1.txt").write_text("first", encoding="utf-8")
            (base_path / "two__v2.txt").write_text("second", encoding="utf-8")

            loader = PromptLoader(base_path)
            templates = loader.load_all()

            self.assertEqual([template.name for template in templates], ["one", "two"])
            self.assertEqual(loader.registry.get("one", "v1").content, "first")
            self.assertEqual(loader.registry.get("two", "v2").content, "second")
