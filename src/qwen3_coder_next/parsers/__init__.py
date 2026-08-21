"""Part 10 parser adapter boundaries."""

from qwen3_coder_next.parsers.contracts import (
    FactKind,
    ParseRequest,
    ParseResult,
    ParserAdapter,
    PythonParserAdapter,
    SyntaxFact,
    UnsupportedLanguageError,
)

__all__ = ["FactKind", "ParseRequest", "ParseResult", "ParserAdapter", "PythonParserAdapter", "SyntaxFact", "UnsupportedLanguageError"]
