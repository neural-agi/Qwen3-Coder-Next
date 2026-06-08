"""Custom exceptions for the in-memory artifact manager."""


class ArtifactNotFoundError(KeyError):
    """Raised when a requested artifact does not exist."""


class DuplicateArtifactError(ValueError):
    """Raised when attempting to create an artifact that already exists."""
