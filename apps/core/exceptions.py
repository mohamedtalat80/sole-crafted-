"""
Custom exception handler.

Guarantees every error response follows exactly:
  {
    "status": false,
    "message": "...",
    "errors": {"field": ["error message"]}
  }

Design (SRP / OCP):
- custom_exception_handler: single entry point registered in DRF settings
- _normalise_errors:  converts any DRF detail structure into the errors dict
- ApplicationError:  base domain exception that services can raise
"""
from __future__ import annotations

import logging
from typing import Any
import django.core.exceptions

from rest_framework import status

logger = logging.getLogger(__name__)
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
    Throttled,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler


# ---------------------------------------------------------------------------
# Domain / Application Exceptions (raise from service layer)
# ---------------------------------------------------------------------------

class ApplicationError(Exception):
    """Base class for all domain-level errors raised from the service layer."""

    def __init__(
        self,
        message: str,
        errors: dict | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        self.message = message
        self.errors = errors or {}
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(ApplicationError):
    def __init__(self, message: str = "Resource not found", errors: dict | None = None) -> None:
        super().__init__(message, errors, status.HTTP_404_NOT_FOUND)


class ConflictError(ApplicationError):
    def __init__(self, message: str = "Conflict", errors: dict | None = None) -> None:
        super().__init__(message, errors, status.HTTP_409_CONFLICT)


class UnauthorizedError(ApplicationError):
    def __init__(self, message: str = "Unauthorized", errors: dict | None = None) -> None:
        super().__init__(message, errors, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(ApplicationError):
    def __init__(self, message: str = "Forbidden", errors: dict | None = None) -> None:
        super().__init__(message, errors, status.HTTP_403_FORBIDDEN)


class TooManyRequestsError(ApplicationError):
    def __init__(self, message: str = "Too many requests", errors: dict | None = None) -> None:
        super().__init__(message, errors, status.HTTP_429_TOO_MANY_REQUESTS)


# ---------------------------------------------------------------------------
# Error normalisation helpers
# ---------------------------------------------------------------------------

def _normalise_detail(detail: Any) -> list[str]:
    """Flatten a DRF ErrorDetail or nested structure into a list of strings."""
    if isinstance(detail, list):
        msgs: list[str] = []
        for item in detail:
            msgs.extend(_normalise_detail(item))
        return msgs
    if isinstance(detail, dict):
        msgs = []
        for v in detail.values():
            msgs.extend(_normalise_detail(v))
        return msgs
    return [str(detail)]


def _normalise_errors(detail: Any) -> dict[str, list[str]]:
    """
    Convert DRF exception detail into {"field": ["msg"]} structure.

    - dict  → keep keys, flatten values
    - list  → use key "non_field_errors"
    - scalar → use key "non_field_errors"
    """
    if isinstance(detail, dict):
        return {field: _normalise_detail(messages) for field, messages in detail.items()}
    return {"non_field_errors": _normalise_detail(detail)}


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------

_STATUS_MESSAGES: dict[int, str] = {
    400: "Validation failed",
    401: "Authentication required",
    403: "You do not have permission to perform this action",
    404: "Resource not found",
    405: "Method not allowed",
    429: "Too many requests",
    500: "Internal server error",
}


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    DRF exception handler registered via settings.REST_FRAMEWORK['EXCEPTION_HANDLER'].

    Handles:
    1. ApplicationError (domain exceptions from service layer)
    2. DRF built-in exceptions (ValidationError, AuthenticationFailed, etc.)
    3. Unexpected exceptions (returns 500)
    """

    # --- 0. Handle Django's ValidationError (raised during model save/clean) ---
    if isinstance(exc, django.core.exceptions.ValidationError):
        # Flatten the error dict/list into our standard structure
        errors = _normalise_errors(exc.message_dict if hasattr(exc, 'message_dict') else exc.messages)
        return Response(
            {
                "status": False,
                "message": "Validation failed",
                "errors": errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --- 1. Domain exceptions raised from service layer ---
    if isinstance(exc, ApplicationError):
        logger.warning(
            "ApplicationError [%s]: %s | errors=%s",
            exc.status_code, exc.message, exc.errors,
        )
        return Response(
            {
                "status": False,
                "message": exc.message,
                "errors": exc.errors,
            },
            status=exc.status_code,
        )

    # --- 2. DRF exceptions (let DRF build the response first) ---
    response = drf_default_handler(exc, context)

    if response is not None:
        http_status: int = response.status_code
        errors = _normalise_errors(response.data)

        # Derive a human-readable top-level message
        if isinstance(exc, ValidationError):
            message = "Validation failed"
        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            message = "Authentication required"
            if isinstance(exc, AuthenticationFailed):
                message = str(exc.detail) if not isinstance(exc.detail, dict) else "Authentication failed"
        elif isinstance(exc, PermissionDenied):
            message = "You do not have permission to perform this action"
        elif isinstance(exc, Throttled):
            message = "Rate limit exceeded. Try again in X seconds."
        else:
            message = _STATUS_MESSAGES.get(http_status, "An error occurred")

        logger.warning(
            "DRF %s [%s]: %s | errors=%s",
            type(exc).__name__, http_status, message, errors,
        )

        return Response(
            {
                "status": False,
                "message": message,
                "errors": errors,
            },
            status=http_status,
        )

    # --- 3. Unhandled exception → 500 ---
    logger.exception("Unhandled exception in %s", context.get("view"))
    return Response(
        {
            "status": False,
            "message": "Internal server error",
            "errors": {},
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
