"""
TranslationService — auto-translates onboarding screen content via OpenAI.

Design notes:
- Uses the Chat Completions API (gpt-4o-mini) for cost-effective, fast results.
- `translate_batch` sends title + description in one API call to minimise
  latency and token cost.
- Never raises — logs exceptions and returns original text as fallback so
  onboarding screens remain readable in English even when translation fails.
- Fully injectable: tests pass a mock instance to OnboardingService directly.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Dict

from apps.core.exceptions import ApplicationError
logger = logging.getLogger(__name__)

_OPENAI_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
_MODEL = "meta/llama-3.1-70b-instruct"
_TIMEOUT = 40  # seconds

# Language codes → human-readable names sent to the model
TRANSLATION_LANGUAGES: Dict[str, str] = {
    "ar": "Arabic",
    "nl": "Dutch",
    "ru": "Russian",
    "pt": "Portuguese",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "ko": "Korean",
    "es": "Spanish",
}


class TranslationService:
    """
    Translates text into supported languages using the OpenAI API.

    Inject via constructor so tests can supply a mock without patching globals.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate_batch(
        self,
        texts: Dict[str, str],
        target_language_name: str,
    ) -> Dict[str, str]:
        """
        Translate multiple labelled strings in a single API call.

        ``texts`` is a dict like ``{"title": "...", "description": "..."}``.
        Returns a dict with the same keys and translated values.

        On any failure (network error, bad API key, malformed response) the
        original values are returned unchanged.
        """
        if not texts:
            return {}

        if not self._api_key:
            logger.warning(
                "API_TRANSLATION_KEY is not configured — returning original text."
            )
            return texts

        # Build a deterministic numbered list so the model knows what to
        # translate, then ask for JSON back with identical keys.
        labelled = "\n".join(f"[{k}]: {v}" for k, v in texts.items())

        payload = {
            "model": _MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are a professional translator specialised in mobile-app UI copy. "
                        f"Translate the following labelled texts to {target_language_name}. "
                        "Return ONLY a valid JSON object with the same keys and translated "
                        "string values.  No markdown fences, no extra keys, no commentary."
                    ),
                },
                {"role": "user", "content": labelled},
            ],
            "max_tokens": 2000,
            "temperature": 0.2,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                _OPENAI_URL,
                data=data,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:
                result = json.loads(response.read().decode("utf-8"))
                raw = result["choices"][0]["message"]["content"].strip()
                translated: Dict[str, str] = json.loads(raw)
                # Guard: fall back per-key if the model dropped any key
                return {k: str(translated.get(k, v)) for k, v in texts.items()}

        except urllib.error.HTTPError as exc:
            content = exc.read().decode("utf-8", errors="replace")
            logger.error(
                "OpenAI API HTTP %s when translating to %s: %s",
                exc.code,
                target_language_name,
                content[:200],
            )
            if exc.code == 401:
                raise ApplicationError(f"Translation service authentication failed: {content}", status_code=401)
        except (urllib.error.URLError, TimeoutError) as exc:
            logger.error("Network error translating to %s: %s", target_language_name, exc)
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "Unexpected OpenAI response structure translating to %s: %s",
                target_language_name,
                exc,
            )
        except Exception:
            logger.exception("Unexpected error translating to %s", target_language_name)

        return texts  # fallback to originals
