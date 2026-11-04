"""Custom exceptions."""


class ExportError(Exception):
    """A user-facing error (bad credentials, HTTP failure, stale request body...)."""
