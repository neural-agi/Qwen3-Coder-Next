"""Custom exceptions for model gateway infrastructure."""


class ModelGatewayError(Exception):
    """Base exception for model gateway errors."""


class InvalidModelRequestError(ModelGatewayError, TypeError):
    """Raised when a model gateway request is not a valid ModelRequest."""
