"""
Firebase Cloud Messaging provider — HTTP v1 API (service account + OAuth2).

Why this replaces the old server-key approach:
  - The legacy endpoint (fcm.googleapis.com/fcm/send) is deprecated by Google.
  - The v1 API uses short-lived OAuth2 bearer tokens derived from a service account,
    which are more secure and rotated automatically.

Token lifecycle:
  - Tokens last 3600 s. A module-level cache (protected by a threading.Lock)
    avoids a new token exchange on every request. Each Gunicorn worker caches
    independently — still correct, just one exchange per worker restart.

Usage:
    provider = FcmProvider(settings.FIREBASE_SERVICE_ACCOUNT)
    provider.send_to_user(user, title="Hello", body="World", data={"key": "val"})

When FIREBASE_SERVICE_ACCOUNT is None (not configured), every call is a no-op.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

import jwt as pyjwt

if TYPE_CHECKING:
    from apps.users.models import CustomUser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level token cache (shared within one process)
# ---------------------------------------------------------------------------

_TOKEN_CACHE: dict = {"token": None, "expires_at": 0.0}
_TOKEN_LOCK = threading.Lock()

_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"


def _get_access_token(sa_info: dict) -> str:
    """
    Return a valid OAuth2 bearer token for Firebase Messaging.

    Creates a signed JWT from the service-account private key, exchanges it
    for an access token at the Google token endpoint, and caches the result
    until 60 seconds before expiry.
    """
    now = time.time()
    with _TOKEN_LOCK:
        if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["expires_at"] - 60:
            return _TOKEN_CACHE["token"]

        assertion = pyjwt.encode(
            {
                "iss": sa_info["client_email"],
                "scope": _FCM_SCOPE,
                "aud": _GOOGLE_TOKEN_URL,
                "iat": int(now),
                "exp": int(now) + 3600,
            },
            sa_info["private_key"],
            algorithm="RS256",
        )

        body = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }).encode()

        req = urllib.request.Request(_GOOGLE_TOKEN_URL, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())

        _TOKEN_CACHE["token"] = result["access_token"]
        _TOKEN_CACHE["expires_at"] = now + result.get("expires_in", 3600)
        return _TOKEN_CACHE["token"]


# ---------------------------------------------------------------------------
# Public provider
# ---------------------------------------------------------------------------

class FcmProvider:
    """
    Thin wrapper around the FCM HTTP v1 API.

    Sends one HTTP request per device token (v1 API does not support multicast).
    All errors are caught and logged — callers never see FCM failures.
    """

    def __init__(self, service_account_info: dict | None) -> None:
        self._sa_info = service_account_info

    @property
    def _is_configured(self) -> bool:
        return bool(self._sa_info)

    def send_to_user(
        self,
        user: "CustomUser",
        title: str,
        body: str,
        data: dict | None = None,
        image_url: str | None = None,
    ) -> None:
        """Fan-out push notification to every registered device of the given user."""
        if not self._is_configured:
            return

        tokens = list(user.devices.values_list("fcm_token", flat=True))
        if not tokens:
            return

        for token in tokens:
            self._send(token, title, body, data or {}, image_url)

    def _send(
        self,
        token: str,
        title: str,
        body: str,
        data: dict,
        image_url: str | None = None,
    ) -> None:
        try:
            access_token = _get_access_token(self._sa_info)
        except Exception:
            logger.exception("FCM: failed to obtain OAuth2 access token")
            return

        project_id = self._sa_info["project_id"]
        url = _FCM_SEND_URL.format(project_id=project_id)

        # FCM data payload values must all be strings
        str_data = {k: str(v) for k, v in data.items()}

        # Include image_url in data so Flutter can render it in foreground
        if image_url:
            str_data["image_url"] = image_url

        notification_block: dict = {"title": title, "body": body}
        # notification.image lets the OS render the image in background/terminated
        if image_url:
            notification_block["image"] = image_url

        payload = json.dumps({
            "message": {
                "token": token,
                "notification": notification_block,
                "data": str_data,
            }
        }).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    logger.warning(
                        "FCM returned HTTP %s for token %.20s…", resp.status, token
                    )
        except Exception:
            logger.exception("FCM: send failed for token %.20s…", token)
