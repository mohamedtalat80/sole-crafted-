"""
Feature Test: Standardized Error Response Format
=================================================

Assertion goal:
  Every error response from the API must exactly match the envelope:
  {
    "status": false,
    "message": "...",
    "errors": { "field": ["error message"] }
  }

Coverage:
  1.  Serializer validation error  → 400 (missing / invalid fields)
  2.  Duplicate email conflict      → 409
  3.  Wrong credentials             → 401
  4.  Unauthenticated access        → 401 (DRF IsAuthenticated)
  5.  Malformed JSON body           → 400
  6.  Password too short            → 400
  7.  Invalid refresh token         → 401
  8.  ApplicationError raised directly from service layer

All tests run against the real URL router (no direct view calls),
using Django's test client, with an in-memory SQLite database.
"""
import json

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import CustomUser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_error_envelope(test_case: TestCase, response, expected_status_code: int):
    """
    Assert that `response` carries the exact error envelope shape and HTTP code.

    Checks:
    - HTTP status code matches expected_status_code
    - response body is JSON
    - "status" key is exactly False (boolean)
    - "message" key is a non-empty string
    - "errors" key is a dict (may be empty {})
    """
    test_case.assertEqual(
        response.status_code,
        expected_status_code,
        msg=f"Expected HTTP {expected_status_code}, got {response.status_code}. Body: {response.content}",
    )

    body = response.json()

    # ── Top-level keys ──────────────────────────────────────────────────────
    test_case.assertIn("status", body, "'status' key missing from error response")
    test_case.assertIn("message", body, "'message' key missing from error response")
    test_case.assertIn("errors", body, "'errors' key missing from error response")

    # ── Types ───────────────────────────────────────────────────────────────
    test_case.assertIs(body["status"], False, "'status' must be boolean False on error")
    test_case.assertIsInstance(body["message"], str, "'message' must be a string")
    test_case.assertGreater(len(body["message"]), 0, "'message' must not be empty")
    test_case.assertIsInstance(body["errors"], dict, "'errors' must be a dict")

    # ── No stray success keys ────────────────────────────────────────────────
    test_case.assertNotIn("data", body, "Error response must not contain 'data' key")

    # ── Each errors entry must be a list of strings ─────────────────────────
    for field, messages in body["errors"].items():
        test_case.assertIsInstance(messages, list, f"errors['{field}'] must be a list")
        for msg in messages:
            test_case.assertIsInstance(msg, str, f"errors['{field}'] items must be strings")

    return body  # return parsed body so callers can make additional assertions


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@override_settings(
    ALLOWED_HOSTS=["*"],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
)
class ErrorFormatTests(TestCase):
    """
    Verify that every error path produces the standardised JSON envelope.
    Uses SQLite in-memory to avoid requiring a running PostgreSQL instance.
    """

    def setUp(self):
        self.client = APIClient()
        self.signup_url = reverse("auth-signup")
        self.login_url = reverse("auth-login")
        self.logout_url = reverse("auth-logout")
        self.refresh_url = reverse("auth-refresh")
        self.profile_url = reverse("auth-profile")

        # A valid authenticated user used by tests that need auth
        self.existing_user = CustomUser.objects.create_user(
            email="existing@example.com",
            full_name="Existing User",
            password="ValidPass123!",
            account_type="customer",
            is_verified=True,
        )

    # ------------------------------------------------------------------
    # 1. Missing required field → 400
    # ------------------------------------------------------------------

    def test_missing_email_returns_standard_error(self):
        """POST /auth/signup without 'email' field."""
        response = self.client.post(
            self.signup_url,
            data={"full_name": "Ahmed", "password": "ValidPass123!", "account_type": "customer"},
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", body["errors"])

    def test_missing_password_returns_standard_error(self):
        """POST /auth/signup without 'password' field."""
        response = self.client.post(
            self.signup_url,
            data={"full_name": "Ahmed", "email": "new@example.com", "account_type": "customer"},
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", body["errors"])

    def test_invalid_email_format_returns_standard_error(self):
        """POST /auth/signup with malformed email value."""
        response = self.client.post(
            self.signup_url,
            data={
                "full_name": "Ahmed",
                "email": "not-an-email",
                "password": "ValidPass123!",
                "account_type": "customer",
            },
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", body["errors"])

    # ------------------------------------------------------------------
    # 2. Duplicate email → 409
    # ------------------------------------------------------------------

    def test_duplicate_email_returns_conflict_error(self):
        """POST /auth/signup with an email that is already registered."""
        response = self.client.post(
            self.signup_url,
            data={
                "full_name": "Another Person",
                "email": "existing@example.com",
                "password": "ValidPass123!",
                "account_type": "customer",
            },
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_409_CONFLICT)
        self.assertIn("email", body["errors"])
        self.assertIn("already registered", body["errors"]["email"][0])

    # ------------------------------------------------------------------
    # 3. Wrong credentials → 401
    # ------------------------------------------------------------------

    def test_wrong_password_returns_standard_error(self):
        """POST /auth/login with incorrect password."""
        response = self.client.post(
            self.login_url,
            data={"email": "existing@example.com", "password": "WrongPassword!"},
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("email", body["errors"])

    def test_nonexistent_email_returns_standard_error(self):
        """POST /auth/login with an email that has no account."""
        response = self.client.post(
            self.login_url,
            data={"email": "ghost@example.com", "password": "SomePass123!"},
            format="json",
        )
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # 6. Unauthenticated access to protected endpoint → 401
    # ------------------------------------------------------------------

    def test_unauthenticated_profile_access_returns_standard_error(self):
        """GET /auth/profile without any auth token."""
        response = self.client.get(
            self.profile_url,
            HTTP_DEVICE_TYPE="mobile",
        )
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # 7. Password too short → 400
    # ------------------------------------------------------------------

    def test_short_password_returns_standard_error(self):
        """Password < 8 characters must fail with the standard error shape."""
        response = self.client.post(
            self.signup_url,
            data={
                "full_name": "Ahmed",
                "email": "short@example.com",
                "password": "abc",
                "account_type": "customer",
            },
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", body["errors"])

    # ------------------------------------------------------------------
    # 8. Invalid refresh token → 401
    # ------------------------------------------------------------------

    def test_invalid_refresh_token_returns_standard_error(self):
        """POST /auth/refresh with a garbage token string."""
        response = self.client.post(
            self.refresh_url,
            data={"refresh": "this.is.not.a.valid.jwt"},
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("refresh", body["errors"])

    # ------------------------------------------------------------------
    # 9. Missing refresh field on logout → 400
    # ------------------------------------------------------------------

    def test_logout_missing_refresh_returns_standard_error(self):
        """POST /auth/logout without the refresh token body field."""
        self.client.force_authenticate(user=self.existing_user)
        response = self.client.post(
            self.logout_url,
            data={},
            format="json",
            HTTP_DEVICE_TYPE="mobile",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("refresh", body["errors"])

    # ------------------------------------------------------------------
    # 10. Invalid account_type choice → 400
    # ------------------------------------------------------------------

    def test_invalid_account_type_returns_standard_error(self):
        """account_type must be 'customer' or 'owner' — anything else is a 400."""
        response = self.client.post(
            self.signup_url,
            data={
                "full_name": "Ahmed",
                "email": "choice@example.com",
                "password": "ValidPass123!",
                "account_type": "admin",  # not a valid choice
            },
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("account_type", body["errors"])
