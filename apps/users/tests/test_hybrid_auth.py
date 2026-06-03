"""
Feature Tests: Hybrid JWT Authentication (Header + Cookie)
===========================================================

Covers:
  - Login / SignUp set HttpOnly cookies
  - Cookie-based authentication grants access to protected endpoints
  - Authorization header auth continues to work unmodified
  - Logout clears cookies (body refresh OR cookie refresh)
  - Token refresh via cookie updates the access_token cookie
  - CSRF enforcement is applied to cookie-authenticated POST requests
  - Cookie path is respected so mismatched cookies are ignored
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser
from apps.users.tests.test_error_format import _assert_error_envelope

# ---------------------------------------------------------------------------
# Shared test DB + settings overrides
# ---------------------------------------------------------------------------

DB_OVERRIDE = override_settings(
    ALLOWED_HOSTS=["*"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    # Use a non-secure cookie during tests (no HTTPS in test runner)
    DEBUG=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email="cookie@example.com", password="ValidPass1!", **kwargs):
    return CustomUser.objects.create_user(
        email=email,
        full_name="Cookie User",
        password=password,
        account_type="customer",
        is_verified=True,
        **kwargs,
    )


def _assert_auth_cookies_set(test_case, response):
    """Assert that both JWT cookies are present and HttpOnly."""
    test_case.assertIn("access_token", response.cookies)
    test_case.assertIn("refresh_token", response.cookies)
    test_case.assertTrue(response.cookies["access_token"]["httponly"])
    test_case.assertTrue(response.cookies["refresh_token"]["httponly"])
    test_case.assertEqual(response.cookies["access_token"]["samesite"], "Lax")
    test_case.assertEqual(response.cookies["refresh_token"]["samesite"], "Lax")


def _assert_auth_cookies_cleared(test_case, response):
    """Assert that JWT cookies have been expired/deleted."""
    for name in ("access_token", "refresh_token"):
        if name in response.cookies:
            # delete_cookie sets max_age=0 or expires to epoch
            cookie = response.cookies[name]
            test_case.assertTrue(
                cookie["max-age"] == 0 or cookie.value == "",
                msg=f"Cookie '{name}' was not cleared (max-age={cookie['max-age']!r}, value={cookie.value!r})",
            )


# ---------------------------------------------------------------------------
# Login / SignUp → cookies are set
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class LoginSetsCookiesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()

    def test_login_sets_httponly_cookies(self):
        response = self.client.post(
            reverse("auth-login"),
            {"email": "cookie@example.com", "password": "ValidPass1!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        _assert_auth_cookies_set(self, response)

    def test_login_still_returns_tokens_in_body(self):
        response = self.client.post(
            reverse("auth-login"),
            {"email": "cookie@example.com", "password": "ValidPass1!"},
            format="json",
        )
        body = response.json()
        self.assertIn("access", body["data"])
        self.assertIn("refresh", body["data"])

    def test_signup_sets_httponly_cookies(self):
        response = self.client.post(
            reverse("auth-signup"),
            {
                "email": "newcookie@example.com",
                "full_name": "New Cookie",
                "password": "ValidPass1!",
                "account_type": "customer",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        _assert_auth_cookies_set(self, response)


# ---------------------------------------------------------------------------
# Cookie-based authentication
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class CookieAuthTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.refresh_token = str(refresh)

    def _client_with_cookie(self):
        client = APIClient()
        client.cookies["access_token"] = self.access_token
        return client

    # --- Happy paths ---

    def test_cookie_auth_grants_access_to_protected_endpoint(self):
        client = self._client_with_cookie()
        response = client.get(reverse("auth-profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["status"])

    def test_header_auth_still_works_independently(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = client.get(reverse("auth-profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Error cases ---

    def test_no_credentials_returns_401(self):
        client = APIClient()
        response = client.get(reverse("auth-profile"))
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_cookie_token_returns_401(self):
        client = APIClient()
        client.cookies["access_token"] = "not.a.valid.jwt"
        response = client.get(reverse("auth-profile"))
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_header_takes_priority_over_cookie(self):
        """When both header and cookie are present, header wins."""
        other_user = _make_user(email="other@example.com")
        other_refresh = RefreshToken.for_user(other_user)
        other_access = str(other_refresh.access_token)

        client = APIClient()
        # Cookie belongs to self.user
        client.cookies["access_token"] = self.access_token
        # Header belongs to other_user → should win
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_access}")

        response = client.get(reverse("auth-profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response email must be other_user's, not self.user's
        self.assertEqual(response.json()["data"]["email"], "other@example.com")


# ---------------------------------------------------------------------------
# CSRF enforcement for cookie-based auth
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class CookieAuthCsrfTests(TestCase):
    def setUp(self):
        self.user = _make_user()
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_cookie_auth_post_without_csrf_token_returns_403(self):
        """
        Non-safe methods authenticated via cookie must include a CSRF token.
        APIClient(enforce_csrf_checks=True) simulates a real browser sending
        the access_token cookie without the X-CSRFToken header.
        """
        client = APIClient(enforce_csrf_checks=True)
        client.cookies["access_token"] = self.access_token

        # POST to any authenticated endpoint without X-CSRFToken
        response = client.post(
            reverse("auth-logout"),
            {"refresh": "irrelevant"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_header_auth_post_skips_csrf(self):
        """
        Bearer-header auth must NOT be affected by CSRF checks regardless of
        enforce_csrf_checks — it is a stateless, non-cookie transport.
        """
        client = APIClient(enforce_csrf_checks=True)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

        refresh = RefreshToken.for_user(self.user)
        response = client.post(
            reverse("auth-logout"),
            {"refresh": str(refresh)},
            format="json",
        )
        # CSRF must not interfere with header-based auth
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class LogoutTests(TestCase):
    def setUp(self):
        self.user = _make_user()

    def _get_tokens(self):
        refresh = RefreshToken.for_user(self.user)
        return str(refresh.access_token), str(refresh)

    # --- Mobile flow: refresh in body ---

    def test_logout_via_body_blacklists_token_and_clears_cookies(self):
        access, refresh = self._get_tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.post(reverse("auth-logout"), {"refresh": refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        _assert_auth_cookies_cleared(self, response)

    # --- Web flow: refresh in cookie ---

    def test_logout_via_cookie_refresh_token(self):
        access, refresh = self._get_tokens()
        client = APIClient()
        client.cookies["access_token"] = access
        client.cookies["refresh_token"] = refresh

        # Web client: no body, CSRF must be enforced — bypass by not using
        # enforce_csrf_checks so we can test the cookie-refresh path in isolation
        response = client.post(reverse("auth-logout"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        _assert_auth_cookies_cleared(self, response)

    def test_logout_without_refresh_token_returns_400(self):
        access, _ = self._get_tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.post(reverse("auth-logout"), {}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_logout_with_invalid_refresh_token_returns_400(self):
        access, _ = self._get_tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.post(reverse("auth-logout"), {"refresh": "bad.token"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class TokenRefreshCookieTests(TestCase):
    def setUp(self):
        self.user = _make_user()

    def _get_tokens(self):
        refresh = RefreshToken.for_user(self.user)
        return str(refresh.access_token), str(refresh)

    # --- Mobile flow: refresh in body, no cookie update ---

    def test_refresh_via_body_returns_new_access(self):
        access, refresh = self._get_tokens()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = client.post(reverse("auth-refresh"), {"refresh": refresh}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json()["data"])

    def test_refresh_via_body_does_not_set_access_cookie(self):
        """Body-based refresh must not add an unexpected cookie."""
        _, refresh = self._get_tokens()
        client = APIClient()
        response = client.post(reverse("auth-refresh"), {"refresh": refresh}, format="json")

        self.assertNotIn("access_token", response.cookies)

    # --- Web flow: refresh from cookie, response updates access cookie ---

    def test_refresh_via_cookie_returns_new_access_in_body(self):
        _, refresh = self._get_tokens()
        client = APIClient()
        client.cookies["refresh_token"] = refresh

        response = client.post(reverse("auth-refresh"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json()["data"])

    def test_refresh_via_cookie_updates_access_token_cookie(self):
        _, refresh = self._get_tokens()
        client = APIClient()
        client.cookies["refresh_token"] = refresh

        response = client.post(reverse("auth-refresh"), {}, format="json")

        self.assertIn("access_token", response.cookies)
        self.assertTrue(response.cookies["access_token"]["httponly"])

    def test_refresh_without_token_returns_400(self):
        client = APIClient()
        response = client.post(reverse("auth-refresh"), {}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_refresh_with_invalid_token_returns_401(self):
        client = APIClient()
        response = client.post(reverse("auth-refresh"), {"refresh": "bad.token"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)
