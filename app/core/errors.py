"""Shared exception types for the platform."""


class TEBError(Exception):
    """Base exception for all TEB application errors."""


class DatasetValidationError(TEBError):
    """Raised when a dataset record or file fails validation."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class ProviderError(TEBError):
    """Raised when a provider adapter fails (network, auth, invalid response)."""

    def __init__(self, message: str, *, provider: str = "", status_code: int | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class CostLimitExceededError(TEBError):
    """Raised when a job would exceed the configured spending limit."""


class JobStateError(TEBError):
    """Raised on invalid job transitions (e.g. resuming a finished job)."""


class NotFoundError(TEBError):
    """Raised when a requested entity does not exist."""
