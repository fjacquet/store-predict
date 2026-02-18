"""Custom exceptions for the ingestion pipeline."""


class IngestionError(Exception):
    """Raised when file ingestion fails with a user-facing message.

    Attributes:
        message: User-facing error description.
        details: Developer-facing details for logging/debugging.
    """

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.details = details
