"""Base interfaces for model adapters."""

from abc import ABC, abstractmethod

from qwen3_coder_next.contracts import ModelRequest, ModelResponse


class BaseModelAdapter(ABC):
    """Abstract interface for model adapter implementations."""

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a response for a validated model request."""
