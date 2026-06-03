"""
Custom JWT authentication backends.

InvalidatedTokenAuthentication
    Extends simplejwt's default JWTAuthentication with one extra check:
    if the user has called logout-from-all-devices, any access token issued
    BEFORE that timestamp is rejected immediately — even if the token itself
    has not yet expired.

    This is necessary because JWT access tokens are stateless; the token
    blacklist only covers refresh tokens. Without this check, a client whose
    refresh tokens are all blacklisted could still call authenticated endpoints
    with an existing access token for up to ACCESS_TOKEN_LIFETIME (1 hour).

HybridJWTAuthentication
    Extends InvalidatedTokenAuthentication to support two transport modes:

    - Mobile  : reads the access token from the ``Authorization: Bearer``
                header. No cookies, no CSRF overhead.
    - Web     : reads the access token from the ``access_token`` HttpOnly
                cookie. CSRF is enforced for non-safe HTTP methods to
                prevent cross-site request forgery (same mechanism as
                DRF's built-in SessionAuthentication).

    The header is always tried first. The cookie fallback is only reached
    when no Authorization header is present, so existing mobile clients are
    completely unaffected.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension

logger = logging.getLogger(__name__)


class HybridJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.core.authentication.HybridJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT via Authorization header (mobile) or access_token HttpOnly cookie (web).",
        }


class InvalidatedTokenAuthentication(JWTAuthentication):
    """
    Drop-in replacement for JWTAuthentication.

    After the standard token validation passes, checks the token's `iat`
    (issued-at) claim against `user.tokens_invalidated_at`.  If the token
    was issued before the user last triggered logout-from-all-devices, the
    request is rejected with 401.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)

        invalidated_at = user.tokens_invalidated_at
        if invalidated_at is None:
            return user

        # `iat` is a Unix timestamp (int) in the JWT payload.
        iat = validated_token.get("iat")
        if iat is None:
            return user

        token_issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)

        # Make invalidated_at timezone-aware for a safe comparison.
        if invalidated_at.tzinfo is None:
            invalidated_at = invalidated_at.replace(tzinfo=timezone.utc)

        if token_issued_at < invalidated_at:
            raise AuthenticationFailed(
                "Token has been invalidated. Please log in again.",
                code="token_invalidated",
            )

        return user


class HybridJWTAuthentication(InvalidatedTokenAuthentication):
    """
    Authenticates via Authorization header (mobile) OR access_token cookie (web).

    Priority:
      1. If an ``Authorization`` header is present → standard Bearer flow.
         CSRF is not checked (stateless API client assumption).
      2. If the ``access_token`` cookie is present → cookie flow.
         CSRF is enforced for non-safe HTTP methods via
         ``SessionAuthentication.enforce_csrf``, which mirrors Django's own
         session-cookie protection without requiring session middleware.

    All token-invalidation logic from InvalidatedTokenAuthentication still
    applies in both paths (the ``get_user`` override is inherited).
    """

    def authenticate(self, request):
        # --- Path 1: header-based auth (mobile / headless API clients) ---
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        # --- Path 2: cookie-based auth (web browsers) ---
        raw_token = request.COOKIES.get("access_token")
        if raw_token is None:
            return None

        # Enforce CSRF for mutating methods — safe methods (GET/HEAD/OPTIONS)
        # are exempt by Django's CsrfViewMiddleware logic used internally.
        self._enforce_csrf(request)

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

    @staticmethod
    def _enforce_csrf(request) -> None:
        """
        Delegate CSRF enforcement to DRF's SessionAuthentication helper.

        Raises ``PermissionDenied`` with a 403 if the CSRF check fails,
        keeping the error format consistent with the rest of the API.
        """
        from rest_framework.authentication import SessionAuthentication
        SessionAuthentication().enforce_csrf(request)
