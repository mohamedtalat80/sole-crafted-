"""
Feature Tests: Signup, Login, Logout, Token Refresh
=====================================================

Covers POST /api/auth/signup, /login, /logout, /refresh.
Each test runs against the full request → response cycle using
Django's test client with an in-memory SQLite database.
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser, EmailVerification, CustomerProfile, OwnerProfile
from apps.users.tests.test_error_format import _assert_error_envelope

DB_OVERRIDE = override_settings(
    ALLOWED_HOSTS=["*"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email="test@example.com", password="ValidPass1!", account_type="customer", **kwargs):
    return CustomUser.objects.create_user(
        email=email,
        full_name="Test User",
        password=password,
        account_type=account_type,
        is_verified=True,
        **kwargs,
    )


def _make_verified_email(email):
    """Create a verified EmailVerification record (prerequisite for signup)."""
    EmailVerification.objects.filter(email=email).delete()
    v = EmailVerification.objects.create(email=email, code="123456")
    v.is_verified = True
    v.save()
    return v


def _tokens(user):
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


# ---------------------------------------------------------------------------
# Signup Tests
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class SignUpTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-signup")

    def test_customer_signup_happy_path(self):
        """Customer signup returns 201 with access + refresh + user profile."""
        _make_verified_email("newuser@example.com")
        response = self.client.post(self.url, data={
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "ValidPass1!",
            "account_type": "customer",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertTrue(body["status"])
        self.assertIn("access", body["data"])
        self.assertIn("refresh", body["data"])
        self.assertEqual(body["data"]["user"]["email"], "newuser@example.com")
        self.assertTrue(body["data"]["user"]["is_verified"])

    def test_owner_signup_not_verified(self):
        """Owner signup → is_verified=False (requires admin document approval)."""
        _make_verified_email("owner@example.com")
        response = self.client.post(self.url, data={
            "email": "owner@example.com",
            "full_name": "Owner User",
            "password": "ValidPass1!",
            "account_type": "owner",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.json()["data"]["user"]["is_verified"])

    def test_captain_signup_not_verified(self):
        """Captain signup → is_verified=False (assigned by owner)."""
        _make_verified_email("captain@example.com")
        response = self.client.post(self.url, data={
            "email": "captain@example.com",
            "full_name": "Captain User",
            "password": "ValidPass1!",
            "account_type": "captain",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.json()["data"]["user"]["is_verified"])

    def test_signup_without_email_verification_fails(self):
        """Signup without a verified EmailVerification record returns 400."""
        response = self.client.post(self.url, data={
            "email": "unverified@example.com",
            "full_name": "Some User",
            "password": "ValidPass1!",
            "account_type": "customer",
        }, format="json")

        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.json()["errors"])

    def test_signup_with_unconfirmed_code_fails(self):
        """Signup with an unverified code (is_verified=False) returns 400."""
        EmailVerification.objects.create(email="pending@example.com", code="000000")
        response = self.client.post(self.url, data={
            "email": "pending@example.com",
            "full_name": "Some User",
            "password": "ValidPass1!",
            "account_type": "customer",
        }, format="json")

        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_email_returns_409(self):
        """Signing up with an already-registered email returns 409."""
        _make_user(email="dup@example.com")
        _make_verified_email("dup@example.com")
        response = self.client.post(self.url, data={
            "email": "dup@example.com",
            "full_name": "Another User",
            "password": "ValidPass1!",
            "account_type": "customer",
        }, format="json")

        _assert_error_envelope(self, response, status.HTTP_409_CONFLICT)
        self.assertIn("email", response.json()["errors"])

    def test_weak_password_returns_400(self):
        """Password '12345678' fails Django's CommonPasswordValidator."""
        _make_verified_email("weak@example.com")
        response = self.client.post(self.url, data={
            "email": "weak@example.com",
            "full_name": "Some User",
            "password": "12345678",
            "account_type": "customer",
        }, format="json")

        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_email_normalized_to_lowercase(self):
        """Email is stored lowercase regardless of what was sent."""
        _make_verified_email("upper@example.com")
        self.client.post(self.url, data={
            "email": "UPPER@EXAMPLE.COM",
            "full_name": "Upper User",
            "password": "ValidPass1!",
            "account_type": "customer",
        }, format="json")

        self.assertTrue(CustomUser.objects.filter(email="upper@example.com").exists())

    def test_signup_creates_customer_profile(self):
        """Signup should auto-create a CustomerProfile via signal."""
        _make_verified_email("profile@example.com")
        self.client.post(self.url, data={
            "email": "profile@example.com",
            "full_name": "Profile User",
            "password": "ValidPass1!",
            "account_type": "customer",
        }, format="json")

        user = CustomUser.objects.get(email="profile@example.com")
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

    def test_signup_creates_owner_profile(self):
        """Signup as owner should auto-create an OwnerProfile via signal."""
        _make_verified_email("owner2@example.com")
        self.client.post(self.url, data={
            "email": "owner2@example.com",
            "full_name": "Owner Two",
            "password": "ValidPass1!",
            "account_type": "owner",
        }, format="json")

        user = CustomUser.objects.get(email="owner2@example.com")
        self.assertTrue(OwnerProfile.objects.filter(user=user).exists())

    def test_email_verification_deleted_after_signup(self):
        """EmailVerification record is deleted after successful signup."""
        _make_verified_email("cleanup@example.com")
        self.client.post(self.url, data={
            "email": "cleanup@example.com",
            "full_name": "Cleanup User",
            "password": "ValidPass1!",
            "account_type": "customer",
        }, format="json")

        self.assertFalse(EmailVerification.objects.filter(email="cleanup@example.com").exists())


# ---------------------------------------------------------------------------
# Login Tests
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-login")
        self.user = _make_user(email="login@example.com", password="ValidPass1!")

    def test_login_happy_path(self):
        """Valid credentials → 200 with access + refresh + user profile."""
        response = self.client.post(self.url, data={
            "email": "login@example.com",
            "password": "ValidPass1!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body["status"])
        self.assertIn("access", body["data"])
        self.assertIn("refresh", body["data"])
        self.assertEqual(body["data"]["user"]["email"], "login@example.com")

    def test_wrong_password_returns_401(self):
        """Wrong password → 401 with error envelope."""
        response = self.client.post(self.url, data={
            "email": "login@example.com",
            "password": "WrongPass!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_email_returns_401(self):
        """Non-existent email → 401 (no email enumeration)."""
        response = self.client.post(self.url, data={
            "email": "ghost@example.com",
            "password": "ValidPass1!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_deactivated_account_cannot_login(self):
        """Deactivated user (is_active=False) → 401."""
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, data={
            "email": "login@example.com",
            "password": "ValidPass1!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_missing_fields_returns_400(self):
        """Empty body → 400 with field errors."""
        response = self.client.post(self.url, data={}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_email_case_insensitive_login(self):
        """Login should work regardless of email case."""
        response = self.client.post(self.url, data={
            "email": "LOGIN@EXAMPLE.COM",
            "password": "ValidPass1!",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Logout Tests
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-logout")
        self.user = _make_user()
        self.access, self.refresh = _tokens(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        self.client.defaults["HTTP_DEVICE_TYPE"] = "web"

    def test_logout_happy_path(self):
        """Logout with valid refresh token → 200 and token is blacklisted."""
        response = self.client.post(self.url, data={"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["status"])

    def test_logout_invalid_token_returns_400(self):
        """Logout with invalid token → 400."""
        response = self.client.post(self.url, data={"refresh": "not.a.token"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_logout_unauthenticated_returns_401(self):
        """Logout without JWT → 401."""
        self.client.credentials()
        response = self.client.post(self.url, data={"refresh": self.refresh}, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_blacklisted_token_cannot_be_reused(self):
        """Token used to logout cannot be used again."""
        self.client.post(self.url, data={"refresh": self.refresh}, format="json")
        # Attempt second logout with same token
        response = self.client.post(self.url, data={"refresh": self.refresh}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Refresh Token Tests
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class RefreshTokenTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-refresh")
        self.user = _make_user()
        self.access, self.refresh = _tokens(self.user)

    def test_refresh_happy_path(self):
        """Valid refresh token → 200 with new access token."""
        response = self.client.post(self.url, data={"refresh": self.refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body["status"])
        self.assertIn("access", body["data"])

    def test_refresh_invalid_token_returns_401(self):
        """Invalid refresh token → 401."""
        response = self.client.post(self.url, data={"refresh": "invalid.token.here"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_missing_token_returns_400(self):
        """Missing refresh token → 400."""
        response = self.client.post(self.url, data={}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
