"""
Feature Tests: Password Flows
==============================

Covers:
  - POST /api/auth/forgot-password       (step 1 — send code)
  - POST /api/auth/verify-reset-code     (step 2 — confirm code)
  - POST /api/auth/set-new-password      (step 3 — set new password via code)
  - POST /api/auth/reset-password        (change password with old password)
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import CustomUser, PasswordResetCode
from apps.users.tests.test_error_format import _assert_error_envelope

DB_OVERRIDE = override_settings(
    ALLOWED_HOSTS=["*"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email="pw@example.com", password="ValidPass1!"):
    return CustomUser.objects.create_user(
        email=email, full_name="PW User",
        password=password, account_type="customer",
        is_verified=True,
    )


def _make_verified_reset(email, code="123456"):
    PasswordResetCode.objects.filter(email=email).delete()
    r = PasswordResetCode.objects.create(email=email, code=code)
    r.is_verified = True
    r.save()
    return r


def _make_unverified_reset(email, code="123456"):
    PasswordResetCode.objects.filter(email=email).delete()
    return PasswordResetCode.objects.create(email=email, code=code)


# ---------------------------------------------------------------------------
# Forgot Password (step 1)
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class ForgotPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-forgot-password")

    def test_always_returns_200_for_registered_email(self):
        """Known active email → 200 (and code is created)."""
        _make_user(email="forgot@example.com")
        response = self.client.post(self.url, data={"email": "forgot@example.com"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["status"])
        self.assertTrue(PasswordResetCode.objects.filter(email="forgot@example.com").exists())

    def test_always_returns_200_for_nonexistent_email(self):
        """Unknown email → still 200 (prevents email enumeration). No code created."""
        response = self.client.post(self.url, data={"email": "ghost@example.com"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PasswordResetCode.objects.filter(email="ghost@example.com").exists())

    def test_always_returns_200_for_deactivated_account(self):
        """Deactivated account → still 200. No code sent."""
        _make_user(email="inactive@example.com")
        CustomUser.objects.filter(email="inactive@example.com").update(is_active=False)
        response = self.client.post(self.url, data={"email": "inactive@example.com"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PasswordResetCode.objects.filter(email="inactive@example.com").exists())

    def test_response_contains_expires_in(self):
        """Response data should include expires_in: 900."""
        _make_user(email="expiry@example.com")
        response = self.client.post(self.url, data={"email": "expiry@example.com"}, format="json")
        self.assertEqual(response.json()["data"]["expires_in"], 900)

    def test_invalid_email_format_returns_400(self):
        """Malformed email → 400."""
        response = self.client.post(self.url, data={"email": "not-an-email"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Verify Reset Code (step 2)
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class VerifyResetCodeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-verify-reset-code")

    def test_happy_path(self):
        """Correct code → 200 with can_reset=True."""
        _make_user(email="vreset@example.com")
        _make_unverified_reset("vreset@example.com", code="654321")
        response = self.client.post(self.url, data={
            "email": "vreset@example.com",
            "code": "654321",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body["status"])
        self.assertTrue(body["data"]["can_reset"])

    def test_code_marked_verified_in_db(self):
        """DB record should have is_verified=True after successful verify."""
        _make_user(email="dbverify@example.com")
        _make_unverified_reset("dbverify@example.com", code="111222")
        self.client.post(self.url, data={"email": "dbverify@example.com", "code": "111222"}, format="json")

        reset = PasswordResetCode.objects.get(email="dbverify@example.com")
        self.assertTrue(reset.is_verified)

    def test_wrong_code_returns_400(self):
        """Wrong code → 400."""
        _make_user(email="wrongc@example.com")
        _make_unverified_reset("wrongc@example.com", code="000000")
        response = self.client.post(self.url, data={"email": "wrongc@example.com", "code": "999999"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_expired_code_returns_400(self):
        """Code older than 900 seconds → 400."""
        _make_user(email="oldcode@example.com")
        r = _make_unverified_reset("oldcode@example.com", code="555555")
        PasswordResetCode.objects.filter(pk=r.pk).update(
            created_at=timezone.now() - timezone.timedelta(seconds=901)
        )
        response = self.client.post(self.url, data={"email": "oldcode@example.com", "code": "555555"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_no_record_returns_400(self):
        """No PasswordResetCode record → 400."""
        response = self.client.post(self.url, data={"email": "norec@example.com", "code": "123456"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Set New Password (step 3 — forgot-password completion)
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class SetNewPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-set-new-password")

    def test_happy_path(self):
        """Verified code + valid new password → 200 and password is changed."""
        user = _make_user(email="setnew@example.com", password="OldPass1!")
        _make_verified_reset("setnew@example.com")
        response = self.client.post(self.url, data={
            "email": "setnew@example.com",
            "new_password": "BrandNew1!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # User should now be able to login with the new password
        user.refresh_from_db()
        self.assertTrue(user.check_password("BrandNew1!"))

    def test_reset_code_deleted_after_success(self):
        """PasswordResetCode should be deleted after a successful reset."""
        _make_user(email="cleanup@example.com")
        _make_verified_reset("cleanup@example.com")
        self.client.post(self.url, data={
            "email": "cleanup@example.com",
            "new_password": "BrandNew1!",
        }, format="json")

        self.assertFalse(PasswordResetCode.objects.filter(email="cleanup@example.com").exists())

    def test_without_verified_code_returns_400(self):
        """Unverified code → 400 (must complete step 2 first)."""
        _make_user(email="nocode@example.com")
        _make_unverified_reset("nocode@example.com")
        response = self.client.post(self.url, data={
            "email": "nocode@example.com",
            "new_password": "BrandNew1!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_without_any_code_record_returns_400(self):
        """No PasswordResetCode at all → 400."""
        _make_user(email="norec@example.com")
        response = self.client.post(self.url, data={
            "email": "norec@example.com",
            "new_password": "BrandNew1!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_returns_400(self):
        """Weak new password fails Django validators → 400."""
        _make_user(email="weaknew@example.com")
        _make_verified_reset("weaknew@example.com")
        response = self.client.post(self.url, data={
            "email": "weaknew@example.com",
            "new_password": "12345678",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_code_cannot_be_reused(self):
        """Second call with the same email (code deleted after first success) → 400."""
        _make_user(email="reuse@example.com")
        _make_verified_reset("reuse@example.com")
        self.client.post(self.url, data={"email": "reuse@example.com", "new_password": "BrandNew1!"}, format="json")
        # Second attempt — code is gone
        response = self.client.post(self.url, data={"email": "reuse@example.com", "new_password": "AnotherNew1!"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Reset Password — change with old password
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class ResetPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-reset-password")

    def test_happy_path(self):
        """Correct old password + valid new password → 200 and password changed."""
        user = _make_user(email="change@example.com", password="OldPass1!")
        response = self.client.post(self.url, data={
            "email": "change@example.com",
            "old_password": "OldPass1!",
            "new_password": "NewPass1!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass1!"))

    def test_wrong_old_password_returns_401(self):
        """Incorrect old password → 401."""
        _make_user(email="wrongold@example.com", password="CorrectPass1!")
        response = self.client.post(self.url, data={
            "email": "wrongold@example.com",
            "old_password": "WrongOldPass1!",
            "new_password": "NewPass1!",
        }, format="json")
        body = _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("old_password", body["errors"])

    def test_nonexistent_email_returns_401(self):
        """Non-existent email → 401 (treated as wrong credentials)."""
        response = self.client.post(self.url, data={
            "email": "ghost@example.com",
            "old_password": "SomePass1!",
            "new_password": "NewPass1!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_deactivated_account_returns_401(self):
        """Deactivated account → 401."""
        _make_user(email="inactive@example.com", password="ValidPass1!")
        CustomUser.objects.filter(email="inactive@example.com").update(is_active=False)
        response = self.client.post(self.url, data={
            "email": "inactive@example.com",
            "old_password": "ValidPass1!",
            "new_password": "NewPass1!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_weak_new_password_returns_400(self):
        """Weak new password → 400."""
        _make_user(email="weaknew2@example.com", password="ValidPass1!")
        response = self.client.post(self.url, data={
            "email": "weaknew2@example.com",
            "old_password": "ValidPass1!",
            "new_password": "12345678",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields_returns_400(self):
        """Missing any required field → 400."""
        response = self.client.post(self.url, data={"email": "x@x.com"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
