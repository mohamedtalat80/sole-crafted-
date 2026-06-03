"""
Standardised API response helpers.

Every endpoint must return one of:
  success_response(data, message, status_code)
  error_response(message, errors, status_code)

Both follow the envelope:
  {
    "status": true | false,
    "message": "...",
    "data": {...} | null,   # only on success
    "errors": {...} | null  # only on error
  }
"""
from typing import Any

from rest_framework.response import Response




def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
) -> Response:
    return Response(
        {"status": True, "message": message, "data": data},
        status=status_code,
    )


def error_response(
    message: str = "An error occurred",
    errors: dict | None = None,
    status_code: int = 400,
) -> Response:
    return Response(
        {"status": False, "message": message, "errors": errors or {}},
        status=status_code,
    )
