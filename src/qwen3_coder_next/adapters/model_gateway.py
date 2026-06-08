"""Foundational model gateway and stub adapter."""

from qwen3_coder_next.adapters.base import BaseModelAdapter
from qwen3_coder_next.adapters.exceptions import InvalidModelRequestError
from qwen3_coder_next.contracts import ModelRequest, ModelResponse
from qwen3_coder_next.logging import get_logger


class StubModelAdapter(BaseModelAdapter):
    """Stub model adapter that returns a fixed response."""

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Return a static response without performing inference."""

        return ModelResponse(
            content="Stub response",
            model_name="stub-model",
            success=True,
        )


class ModelGateway:
    """Stable gateway for invoking a model adapter."""

    def __init__(self, adapter: BaseModelAdapter) -> None:
        """Initialize the model gateway with an adapter implementation."""

        self._adapter = adapter
        self._logger = get_logger("qwen3_coder_next.adapters.model_gateway")

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Validate and route a model request through the configured adapter."""

        self._logger.info("Model request received")
        if not isinstance(request, ModelRequest):
            raise InvalidModelRequestError("Model request must be an instance of ModelRequest.")

        self._logger.info("Executing model adapter")
        response = self._adapter.generate(request)
        self._logger.info("Model response returned")
        return response
