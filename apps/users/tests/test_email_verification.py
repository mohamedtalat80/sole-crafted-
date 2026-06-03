"""
Feature Tests: Email Verification Flow
=======================================

Covers POST /api/auth/send-verification-code and /verify-email-code.
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import CustomUser, EmailVerification
from apps.users.tests.test_error_format import _assert_error_envelope

DB_OVERRIDE = override_settings(
    ALLOWED_HOSTS=["*"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)


# ---------------------------------------------------------------------------
# Send Verification Code Tests
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class SendVerificationCodeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-send-verification-code")

    def test_happy_path_new_email(self):
        """Sending a code to an unregistered email → 200."""
        response = self.client.post(self.url, data={"email": "new@example.com"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body["status"])
        self.assertEqual(body["data"]["email"], "new@example.com")
        self.assertEqual(body["data"]["expires_in"], 900)

    def test_verification_record_created(self):
        """A code should be stored in EmailVerification after sending."""
        self.client.post(self.url, data={"email": "store@example.com"}, format="json")
        self.assertTrue(EmailVerification.objects.filter(email="store@example.com").exists())

    def test_resend_replaces_old_code(self):
        """Resending deletes the old record and creates a fresh one (resets expiry)."""
        EmailVerification.objects.create(email="resend@example.com", code="111111")
        self.client.post(self.url, data={"email": "resend@example.com"}, format="json")
        # Should still be exactly one record
        self.assertEqual(EmailVerification.objects.filter(email="resend@example.com").count(), 1)

    def test_already_registered_email_returns_409(self):
        """Sending a code to an already-registered email → 409."""
        CustomUser.objects.create_user(
            email="registered@example.com",
            full_name="Reg User",
            password="ValidPass1!",
            account_type="customer",
        )
        response = self.client.post(self.url, data={"email": "registered@example.com"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_409_CONFLICT)
        self.assertIn("email", response.json()["errors"])

    def test_invalid_email_format_returns_400(self):
        """Malformed email → 400."""
        response = self.client.post(self.url, data={"email": "not-an-email"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_missing_email_returns_400(self):
        """Empty body → 400."""
        response = self.client.post(self.url, data={}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_email_normalized_to_lowercase(self):
        """Email is stored lowercase."""
        self.client.post(self.url, data={"email": "CAPS@EXAMPLE.COM"}, format="json")
        self.assertTrue(EmailVerification.objects.filter(email="caps@example.com").exists())


# ---------------------------------------------------------------------------
# Verify Email Code Tests
# ---------------------------------------------------------------------------

@DB_OVERRIDE
class VerifyEmailCodeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-verify-email-code")

    def _create_verification(self, email, code="654321", is_verified=False):
        EmailVerification.objects.filter(email=email).delete()
        v = EmailVerification.objects.create(email=email, code=code)
        if is_verified:
            v.is_verified = True
            v.save()
        return v

    def test_happy_path(self):
        """Correct code → 200 and is_verified=True in response."""
        self._create_verification("verify@example.com", code="654321")
        response = self.client.post(self.url, data={
            "email": "verify@example.com",
            "verification_code": "654321",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body["status"])
        self.assertTrue(body["data"]["is_verified"])

    def test_record_marked_verified_in_db(self):
        """Successful verification should set is_verified=True in DB."""
        self._create_verification("dbcheck@example.com", code="777888")
        self.client.post(self.url, data={
            "email": "dbcheck@example.com",
            "verification_code": "777888",
        }, format="json")

        v = EmailVerification.objects.get(email="dbcheck@example.com")
        self.assertTrue(v.is_verified)

    def test_wrong_code_returns_400(self):
        """Wrong code → 400 with verification_code error."""
        self._create_verification("wrongcode@example.com", code="123456")
        response = self.client.post(self.url, data={
            "email": "wrongcode@example.com",
            "verification_code": "999999",
        }, format="json")

        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("verification_code", body["errors"])

    def test_expired_code_returns_400(self):
        """Code older than 900 seconds → 400."""
        v = self._create_verification("expired@example.com", code="111111")
        # Manually set created_at to 901 seconds ago
        EmailVerification.objects.filter(pk=v.pk).update(
            created_at=timezone.now() - timezone.timedelta(seconds=901)
        )

        response = self.client.post(self.url, data={
            "email": "expired@example.com",
            "verification_code": "111111",
        }, format="json")

        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_email_returns_400(self):
        """No verification record for this email → 400."""
        response = self.client.post(self.url, data={
            "email": "ghost@example.com",
            "verification_code": "123456",
        }, format="json")

        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_code_too_short_returns_400(self):
        """Code shorter than 6 chars → serializer 400."""
        response = self.client.post(self.url, data={
            "email": "short@example.com",
            "verification_code": "123",
        }, format="json")

        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
