"""Smoke tests for the model gateway abstraction."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from qwen3_coder_next.adapters import InvalidModelRequestError, ModelGateway, StubModelAdapter
from qwen3_coder_next.config import AppSettings, EnvironmentName
from qwen3_coder_next.contracts import ModelRequest, ModelResponse
from qwen3_coder_next.logging import ApplicationLogger


class ModelGatewaySmokeTest(unittest.TestCase):
    """Verifies foundational model gateway behavior."""

    def test_gateway_accepts_valid_request(self) -> None:
        """Accept a valid request and return a contract response."""

        with TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            settings = AppSettings(
                environment=EnvironmentName.TESTING,
                debug=True,
                workspace_root=workspace_root,
                artifacts_dir=workspace_root / "artifacts",
                data_dir=workspace_root / "data",
                logs_dir=workspace_root / "logs",
            )
            ApplicationLogger.initialize(
                settings,
                logger_name="qwen3_coder_next.adapters.model_gateway",
            )

            gateway = ModelGateway(StubModelAdapter())
            request = ModelRequest(
                prompt="hello",
                system_prompt="system",
            )

            response = gateway.generate(request)

            self.assertIsInstance(response, ModelResponse)
            self.assertEqual(response.content, "Stub response")
            self.assertEqual(response.model_name, "stub-model")
            self.assertTrue(response.success)
            ApplicationLogger.shutdown("qwen3_coder_next.adapters.model_gateway")

    def test_stub_adapter_returns_response(self) -> None:
        """Return the expected stub response directly from the adapter."""

        adapter = StubModelAdapter()
        response = adapter.generate(
            ModelRequest(prompt="hello", system_prompt="system"),
        )

        self.assertEqual(
            response,
            ModelResponse(
                content="Stub response",
                model_name="stub-model",
                success=True,
            ),
        )

    def test_invalid_request_raises_exception(self) -> None:
        """Raise when the gateway receives an invalid request type."""

        gateway = ModelGateway(StubModelAdapter())

        with self.assertRaises(InvalidModelRequestError):
            gateway.generate("not-a-model-request")  # type: ignore[arg-type]


if __name__ == "__main__":
    print("Model gateway smoke tests passed.")
    unittest.main(verbosity=2)
