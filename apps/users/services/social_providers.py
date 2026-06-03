"""
Social provider token verification — custom implementation.

Both Google and Apple use the same JWKS-based verification pattern:
  1. Fetch the provider's public JWKS (cached in Django's cache for 1 hour).
  2. Match the token's 'kid' header to the correct public key.
  3. Decode and verify the JWT (RS256, issuer, audience, expiry) using PyJWT.

Each function returns {"email": "...", "name": "..."} on success,
raises UnauthorizedError on any failure.

User creation is handled by our own service/repository layer — these
functions only verify the token and extract user info.
"""
from __future__ import annotations

import logging

import requests as http
from django.conf import settings
from django.core.cache import cache
from jwt.algorithms import RSAAlgorithm
import jwt

from apps.core.exceptions import UnauthorizedError

logger = logging.getLogger(__name__)

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUER   = "https://accounts.google.com"
APPLE_JWKS_URL  = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER    = "https://appleid.apple.com"

_JWKS_CACHE_TTL = 3600  # 1 hour


def _fetch_jwks(url: str, cache_key: str) -> list[dict]:
    """Fetch a JWKS endpoint, caching the key list for 1 hour."""
    keys = cache.get(cache_key)
    if keys is None:
        response = http.get(url, timeout=10)
        response.raise_for_status()
        keys = response.json().get("keys", [])
        cache.set(cache_key, keys, _JWKS_CACHE_TTL)
    return keys


def _get_public_key(keys: list[dict], kid: str | None):
    """Return the RSA public key matching the given kid."""
    key_data = next((k for k in keys if k.get("kid") == kid), None)
    if key_data is None:
        return None
    return RSAAlgorithm.from_jwk(key_data)


# ---------------------------------------------------------------------------
# Google
# ---------------------------------------------------------------------------

def verify_google_token(id_token: str) -> dict:
    """
    Verify a Google ID token via Google's JWKS endpoint (cached).

    Verifies:
      1. JWT signature against Google's public JWKS (www.googleapis.com/oauth2/v3/certs)
      2. Issuer (https://accounts.google.com)
      3. Audience (GOOGLE_CLIENT_IDS from settings — accepts web + Android + iOS client IDs)
      4. Token expiry

    Caches the JWKS for 1 hour to avoid a live HTTP call on every request.

    Returns:
        {"email": "...", "name": "..."}

    Raises:
        UnauthorizedError: if the token is invalid, expired, or audience mismatch.
    """
    try:
        keys = _fetch_jwks(GOOGLE_JWKS_URL, "social_jwks:google")
        header = jwt.get_unverified_header(id_token)
        public_key = _get_public_key(keys, header.get("kid"))

        if public_key is None:
            raise UnauthorizedError(
                message="Social login failed",
                errors={"provider": ["Google public key not found for this token"]},
            )

        payload = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.GOOGLE_CLIENT_IDS,
            issuer=GOOGLE_ISSUER,
        )

        email = payload.get("email")
        if not email:
            raise UnauthorizedError(
                message="Social login failed",
                errors={"provider": ["Could not retrieve email from Google token"]},
            )

        first_name = payload.get("given_name", "")
        last_name  = payload.get("family_name", "")
        full_name  = f"{first_name} {last_name}".strip()

        return {
            "email": email,
            "name": full_name or payload.get("name", ""),
        }

    except UnauthorizedError:
        raise
    except Exception as exc:
        logger.warning("Google token verification failed: %s", exc)
        raise UnauthorizedError(
            message="Social login failed",
            errors={"provider": [f"Invalid Google token: {exc}"]},
        ) from exc


# ---------------------------------------------------------------------------
# Apple
# ---------------------------------------------------------------------------

def verify_apple_token(identity_token: str) -> dict:
    """
    Verify an Apple identity token using requests + PyJWT.

    The mobile app gets this token from the Apple Sign-In SDK.
    Steps:
      1. Fetch Apple's JWKS public keys from appleid.apple.com/auth/keys
      2. Match the token's 'kid' header to the correct public key
      3. Decode and verify the JWT (RS256, issuer, audience, expiry)

    Args:
        identity_token: The Apple identity token (JWT) from the mobile app.

    Returns:
        {"email": "...", "name": ""}

    Raises:
        UnauthorizedError: if the token is invalid, expired, or unverifiable.

    Note:
        Apple only sends the user's name on the FIRST sign-in via the SDK.
        The JWT itself never contains the name — only email and sub.
    """
    try:
        keys = _fetch_jwks(APPLE_JWKS_URL, "social_jwks:apple")
        header = jwt.get_unverified_header(identity_token)
        public_key = _get_public_key(keys, header.get("kid"))

        if public_key is None:
            raise UnauthorizedError(
                message="Social login failed",
                errors={"provider": ["Apple public key not found for this token"]},
            )

        payload = jwt.decode(
            identity_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.APPLE_CLIENT_ID,
            issuer=APPLE_ISSUER,
        )

        email = payload.get("email")
        if not email:
            raise UnauthorizedError(
                message="Social login failed",
                errors={"provider": ["Could not retrieve email from Apple token"]},
            )

        return {
            "email": email,
            "name": "",  # Apple JWT never contains name — only sent once via SDK callback
        }

    except UnauthorizedError:
        raise
    except Exception as exc:
        logger.warning("Apple token verification failed: %s", exc)
        raise UnauthorizedError(
            message="Social login failed",
            errors={"provider": ["Invalid Apple token"]},
        ) from exc
