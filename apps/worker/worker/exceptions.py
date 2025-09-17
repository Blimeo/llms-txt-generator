# apps/worker/worker/exceptions.py
"""Custom exceptions for the worker application."""


class WorkerError(Exception):
    """Base exception for worker-related errors."""
    pass


class DatabaseError(WorkerError):
    """Database operation errors."""
    pass


class StorageError(WorkerError):
    """Storage operation errors (S3, file system, etc.)."""
    pass


class WebhookError(WorkerError):
    """Webhook-related errors."""
    pass


class SchedulingError(WorkerError):
    """Scheduling and cron-related errors."""
    pass


class CrawlerError(WorkerError):
    """Web crawler errors."""
    pass


class ChangeDetectionError(WorkerError):
    """Change detection errors."""
    pass
