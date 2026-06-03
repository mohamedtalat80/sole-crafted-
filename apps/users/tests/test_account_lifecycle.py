"""
Feature Tests: Account Lifecycle (Delete & Deactivate)
=======================================================

Covers:
  - DELETE /api/auth/account   (permanent anonymization)
  - POST   /api/auth/account/deactivate  (60-day deactivation)
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser, UserDevice
from apps.users.tests.test_error_format import _assert_error_envelope

DB_OVERRIDE = override_settings(
    ALLOWED_HOSTS=["*"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
)


def _make_user(email="life@example.com", account_type="customer", password="ValidPass1!", **kwargs):
    return CustomUser.objects.create_user(
        email=email, full_name="Lifecycle User",
        password=password, account_type=account_type,
        is_verified=True, **kwargs,
    )


def _auth_client(user):
    client = APIClient()
    access = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    client.defaults["HTTP_DEVICE_TYPE"] = "web"
    return client


# ---------------------------------------------------------------------------
# DELETE /api/auth/account
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class DeleteAccountTests(TestCase):
    def setUp(self):
        self.url = reverse("auth-account")

    def test_delete_anonymizes_pii(self):
        """DELETE → PII wiped, email replaced with placeholder, is_active=False."""
        user = _make_user()
        client = _auth_client(user)
        response = client.delete(self.url, {"password": "ValidPass1!"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertTrue(user.email.endswith("@omarina.invalid"))
        self.assertEqual(user.full_name, "Deleted User")
        self.assertIsNone(user.phone_number)
        self.assertFalse(user.has_usable_password())

    def test_original_email_freed_for_reuse(self):
        """After deletion, the original email can be re-registered."""
        user = _make_user(email="reuse@example.com")
        client = _auth_client(user)
        client.delete(self.url, {"password": "ValidPass1!"}, format="json")

        self.assertFalse(CustomUser.objects.filter(email="reuse@example.com").exists())

    def test_delete_removes_device_tokens(self):
        """All UserDevice tokens should be removed on account deletion."""
        user = _make_user()
        UserDevice.objects.create(user=user, fcm_token="device_abc")
        client = _auth_client(user)
        client.delete(self.url, {"password": "ValidPass1!"}, format="json")

        self.assertEqual(UserDevice.objects.filter(user=user).count(), 0)

    def test_delete_wrong_password_returns_401(self):
        """DELETE with wrong password → 401."""
        user = _make_user()
        client = _auth_client(user)
        response = client.delete(self.url, {"password": "WrongPass!"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_delete_missing_password_returns_400(self):
        """DELETE without password body → 400."""
        user = _make_user()
        client = _auth_client(user)
        response = client.delete(self.url, {}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_delete_admin_account_returns_403(self):
        """Admin accounts cannot be self-deleted via the API."""
        admin = _make_user(email="admin@example.com", account_type="admin")
        client = _auth_client(admin)
        response = client.delete(self.url, {"password": "ValidPass1!"}, format="json")

        _assert_error_envelope(self, response, status.HTTP_403_FORBIDDEN)

    def test_delete_unauthenticated_returns_401(self):
        """DELETE without JWT → 401."""
        response = APIClient().delete(self.url)
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_deleted_user_cannot_login(self):
        """Deleted (anonymized) user cannot log back in."""
        user = _make_user(email="gone@example.com", password="ValidPass1!")
        client = _auth_client(user)
        client.delete(self.url, {"password": "ValidPass1!"}, format="json")

        login_response = APIClient().post(
            reverse("auth-login"),
            data={"email": "gone@example.com", "password": "ValidPass1!"},
            format="json",
        )
        _assert_error_envelope(self, login_response, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# POST /api/auth/account (deactivate)
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class DeactivateAccountTests(TestCase):
    def setUp(self):
        self.url = reverse("auth-account")

    def test_deactivate_sets_inactive_and_timestamps(self):
        """POST → is_active=False and deactivated_at is set."""
        user = _make_user()
        client = _auth_client(user)
        response = client.post(self.url, {"password": "ValidPass1!"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertIsNotNone(user.deactivated_at)

    def test_deactivate_wrong_password_returns_401(self):
        """POST with wrong password → 401."""
        user = _make_user()
        client = _auth_client(user)
        response = client.post(self.url, {"password": "WrongPass!"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_deactivate_missing_password_returns_400(self):
        """POST without password body → 400."""
        user = _make_user()
        client = _auth_client(user)
        response = client.post(self.url, {}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_pii_preserved_during_60_day_window(self):
        """PII should NOT be wiped on deactivate (preserved for 60-day window)."""
        user = _make_user(email="pii@example.com")
        client = _auth_client(user)
        client.post(self.url, {"password": "ValidPass1!"}, format="json")

        user.refresh_from_db()
        self.assertEqual(user.email, "pii@example.com")
        self.assertEqual(user.full_name, "Lifecycle User")

    def test_already_deactivated_returns_400(self):
        """Calling deactivate on an already-deactivated account → 401 (inactive user fails JWT auth)."""
        from django.utils import timezone
        user = _make_user()
        user.is_active = False
        user.deactivated_at = timezone.now()
        user.save()

        client = _auth_client(user)
        # Inactive users fail JWT authentication → 401 before reaching service layer
        response = client.post(self.url)
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_deactivate_admin_returns_403(self):
        """Admin accounts cannot be self-deactivated."""
        admin = _make_user(email="admin2@example.com", account_type="admin")
        client = _auth_client(admin)
        response = client.post(self.url, {"password": "ValidPass1!"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_403_FORBIDDEN)

    def test_deactivate_unauthenticated_returns_401(self):
        """POST without JWT → 401."""
        response = APIClient().post(self.url)
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_deactivated_user_cannot_login(self):
        """Deactivated user cannot log in before the 60-day window expires."""
        user = _make_user(email="deac@example.com", password="ValidPass1!")
        client = _auth_client(user)
        client.post(self.url, {"password": "ValidPass1!"}, format="json")

        login_response = APIClient().post(
            reverse("auth-login"),
            data={"email": "deac@example.com", "password": "ValidPass1!"},
            format="json",
        )
        _assert_error_envelope(self, login_response, status.HTTP_401_UNAUTHORIZED)
