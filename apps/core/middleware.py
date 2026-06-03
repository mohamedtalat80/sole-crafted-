"""
Custom middleware.

1. AcceptLanguageMiddleware
   - Reads the `Accept-Language` header and activates Django's translation locale
     so that i18n strings returned in responses respect the client's language.
   - Falls back to settings.LANGUAGE_CODE when the header is absent or invalid.

Design (SRP):
- Each middleware class is responsible for exactly one cross-cutting concern.
- The middleware contains no business logic — it only validates/sets request metadata.
"""
from __future__ import annotations

from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import translation


# ---------------------------------------------------------------------------
# Accept-Language Middleware
# ---------------------------------------------------------------------------

class AcceptLanguageMiddleware:
    """
    Activates Django's translation locale based on the `Accept-Language` header.

    Supported languages are defined in settings.LANGUAGES.
    Falls back to settings.LANGUAGE_CODE when:
      - The header is absent.
      - The requested language is not in LANGUAGES.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        # Build a set of supported language codes from settings, lower-cased.
        self._supported = {code.lower() for code, _ in getattr(settings, "LANGUAGES", [])}

    def __call__(self, request: HttpRequest) -> HttpResponse:
        language = self._resolve_language(request)
        translation.activate(language)
        request.LANGUAGE_CODE = language

        response = self.get_response(request)

        # Ensure Content-Language header reflects active locale
        response["Content-Language"] = language
        translation.deactivate()

        return response

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_language(self, request: HttpRequest) -> str:
        """
        Parse the Accept-Language header and return the best matching
        supported language code, or the default language if none match.
        """
        accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "").strip()

        if not accept_language:
            return settings.LANGUAGE_CODE

        # Parse "en-US,en;q=0.9,ar;q=0.8" → [("en-us", 1.0), ("en", 0.9), ("ar", 0.8)]
        candidates = self._parse_accept_language(accept_language)

        for lang_code, _ in candidates:
            # Try exact match first, then language prefix (e.g. "en-US" → "en")
            if lang_code in self._supported:
                return lang_code
            prefix = lang_code.split("-")[0]
            if prefix in self._supported:
                return prefix

        return settings.LANGUAGE_CODE

    @staticmethod
    def _parse_accept_language(header: str) -> list[tuple[str, float]]:
        """
        Parse Accept-Language header into a sorted list of (language, quality) tuples.
        """
        result: list[tuple[str, float]] = []
        for part in header.split(","):
            part = part.strip()
            if not part:
                continue
            if ";q=" in part:
                lang, q_str = part.rsplit(";q=", 1)
                try:
                    quality = float(q_str.strip())
                except ValueError:
                    quality = 1.0
            else:
                lang = part
                quality = 1.0
            result.append((lang.strip().lower(), quality))

        result.sort(key=lambda x: x[1], reverse=True)
        return result
