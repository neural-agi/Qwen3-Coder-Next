"""Parser adapter contracts for Part 10 Step 2."""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from qwen3_coder_next.graph import SourceUnit


class FactKind(str, Enum):
    """Syntax facts emitted by parser adapters."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    VARIABLE = "variable"
    IMPORT = "import"
    CALL = "call"


@dataclass(frozen=True, slots=True)
class ParseRequest:
    """Input contract for parsing one source unit."""

    source_unit: SourceUnit
    parser_profile: str
    scope: str
    revision_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.source_unit, SourceUnit):
            raise ValueError("source_unit must be a SourceUnit.")
        for name in ("parser_profile", "scope", "revision_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text.")
            object.__setattr__(self, name, value.strip())


@dataclass(frozen=True, slots=True)
class SyntaxFact:
    """One deterministic, source-located parser fact."""

    kind: FactKind
    name: str
    qualified_name: str
    source_path: str
    language: str
    line: int
    column: int
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", self.kind if isinstance(self.kind, FactKind) else FactKind(self.kind))
        for name in ("name", "qualified_name", "source_path", "language"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text.")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.line, int) or self.line < 1 or not isinstance(self.column, int) or self.column < 0:
            raise ValueError("line and column must be valid source positions.")
        if isinstance(self.provenance, (str, bytes)):
            raise ValueError("provenance must be a collection of text.")
        object.__setattr__(self, "provenance", tuple(sorted(set(self.provenance))))

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "name": self.name, "qualified_name": self.qualified_name, "source_path": self.source_path, "language": self.language, "line": self.line, "column": self.column, "provenance": list(self.provenance)}


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Immutable parser output; no graph normalization is performed."""

    source_unit: SourceUnit
    facts: tuple[SyntaxFact, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source_unit, SourceUnit):
            raise ValueError("source_unit must be a SourceUnit.")
        if any(not isinstance(fact, SyntaxFact) for fact in self.facts):
            raise ValueError("facts contains an invalid syntax fact.")
        object.__setattr__(self, "facts", tuple(sorted(self.facts, key=lambda item: (item.line, item.column, item.kind.value, item.qualified_name))))
        if isinstance(self.warnings, (str, bytes)):
            raise ValueError("warnings must be a collection of text.")
        object.__setattr__(self, "warnings", tuple(sorted(set(self.warnings))))


class ParserAdapter:
    """Protocol-like base boundary for language-specific adapters."""

    language = ""

    def parse(self, request: ParseRequest, source_text: str) -> ParseResult:
        raise NotImplementedError


class UnsupportedLanguageError(ValueError):
    """Raised when no adapter supports a source unit language."""


def _qualified(prefix: tuple[str, ...], name: str) -> str:
    return ".".join((*prefix, name)) if prefix else name


class PythonParserAdapter(ParserAdapter):
    """Extract shallow Python syntax facts using the standard-library AST."""

    language = "python"

    def parse(self, request: ParseRequest, source_text: str) -> ParseResult:
        if not isinstance(request, ParseRequest) or not isinstance(source_text, str):
            raise ValueError("request must be ParseRequest and source_text must be text.")
        if request.source_unit.language.lower() != self.language:
            raise UnsupportedLanguageError(request.source_unit.language)
        try:
            tree = ast.parse(source_text, filename=request.source_unit.path)
        except SyntaxError as exc:
            return ParseResult(request.source_unit, (), (f"SyntaxError:{exc.lineno or 0}",))
        facts: list[SyntaxFact] = [SyntaxFact(FactKind.MODULE, request.source_unit.path.rsplit("/", 1)[-1], request.source_unit.path, request.source_unit.path, self.language, 1, 0, (f"{request.source_unit.path}:1",))]

        def visit(node: ast.AST, prefix: tuple[str, ...]) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = FactKind.FUNCTION if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else FactKind.CLASS
                qualified = _qualified(prefix, node.name)
                facts.append(SyntaxFact(kind, node.name, qualified, request.source_unit.path, self.language, node.lineno, node.col_offset, (f"{request.source_unit.path}:{node.lineno}",)))
                for child in node.body:
                    visit(child, (*prefix, node.name))
                return
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = node.names if isinstance(node, (ast.Import, ast.ImportFrom)) else ()
                for alias in names:
                    imported = alias.name
                    facts.append(SyntaxFact(FactKind.IMPORT, imported, imported, request.source_unit.path, self.language, node.lineno, node.col_offset, (f"{request.source_unit.path}:{node.lineno}",)))
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func) if hasattr(ast, "unparse") else type(node.func).__name__
                facts.append(SyntaxFact(FactKind.CALL, name.split(".")[-1], name, request.source_unit.path, self.language, node.lineno, node.col_offset, (f"{request.source_unit.path}:{node.lineno}",)))
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        qualified = _qualified(prefix, target.id)
                        facts.append(SyntaxFact(FactKind.VARIABLE, target.id, qualified, request.source_unit.path, self.language, target.lineno, target.col_offset, (f"{request.source_unit.path}:{target.lineno}",)))
            for child in ast.iter_child_nodes(node):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    visit(child, prefix)

        visit(tree, ())
        return ParseResult(request.source_unit, tuple(facts))
