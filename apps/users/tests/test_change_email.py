"""
Feature Tests: Change Email
============================

Covers POST /api/auth/change-email.
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import CustomUser
from apps.users.tests.test_error_format import _assert_error_envelope

DB_OVERRIDE = override_settings(
    ALLOWED_HOSTS=["*"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
)


def _make_user(email="current@example.com", password="ValidPass1!"):
    return CustomUser.objects.create_user(
        email=email, full_name="Email User",
        password=password, account_type="customer",
        is_verified=True,
    )


@DB_OVERRIDE
class ChangeEmailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-change-email")

    def test_happy_path(self):
        """Valid credentials + unique new email → 200 with new email in response."""
        _make_user(email="old@example.com", password="ValidPass1!")
        response = self.client.post(self.url, data={
            "old_email": "old@example.com",
            "new_email": "new@example.com",
            "password": "ValidPass1!",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body["status"])
        self.assertEqual(body["data"]["email"], "new@example.com")

    def test_email_actually_updated_in_db(self):
        """New email should be persisted to the database."""
        _make_user(email="changeme@example.com", password="ValidPass1!")
        self.client.post(self.url, data={
            "old_email": "changeme@example.com",
            "new_email": "changed@example.com",
            "password": "ValidPass1!",
        }, format="json")

        self.assertTrue(CustomUser.objects.filter(email="changed@example.com").exists())
        self.assertFalse(CustomUser.objects.filter(email="changeme@example.com").exists())

    def test_wrong_password_returns_401(self):
        """Incorrect password → 401."""
        _make_user(email="auth@example.com", password="CorrectPass1!")
        response = self.client.post(self.url, data={
            "old_email": "auth@example.com",
            "new_email": "new@example.com",
            "password": "WrongPass1!",
        }, format="json")

        body = _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("password", body["errors"])

    def test_nonexistent_email_returns_401(self):
        """Non-existent old email → 401."""
        response = self.client.post(self.url, data={
            "old_email": "ghost@example.com",
            "new_email": "new@example.com",
            "password": "SomePass1!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_new_email_already_taken_returns_409(self):
        """New email already registered by another user → 409."""
        _make_user(email="existing@example.com")
        _make_user(email="myemail@example.com", password="MyPass1!")
        response = self.client.post(self.url, data={
            "old_email": "myemail@example.com",
            "new_email": "existing@example.com",
            "password": "MyPass1!",
        }, format="json")

        body = _assert_error_envelope(self, response, status.HTTP_409_CONFLICT)
        self.assertIn("new_email", body["errors"])

    def test_same_old_and_new_email_returns_400(self):
        """Old email == new email → 400 (serializer-level validation)."""
        _make_user(email="same@example.com", password="ValidPass1!")
        response = self.client.post(self.url, data={
            "old_email": "same@example.com",
            "new_email": "same@example.com",
            "password": "ValidPass1!",
        }, format="json")

        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_email", body["errors"])

    def test_deactivated_account_returns_401(self):
        """Deactivated account cannot change email."""
        user = _make_user(email="deac@example.com", password="ValidPass1!")
        user.is_active = False
        user.save()

        response = self.client.post(self.url, data={
            "old_email": "deac@example.com",
            "new_email": "newemail@example.com",
            "password": "ValidPass1!",
        }, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    def test_missing_fields_returns_400(self):
        """Missing required fields → 400."""
        response = self.client.post(self.url, data={"old_email": "x@x.com"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_new_email_normalized_to_lowercase(self):
        """New email should be stored lowercase."""
        _make_user(email="norm@example.com", password="ValidPass1!")
        self.client.post(self.url, data={
            "old_email": "norm@example.com",
            "new_email": "NEW@EXAMPLE.COM",
            "password": "ValidPass1!",
        }, format="json")

        self.assertTrue(CustomUser.objects.filter(email="new@example.com").exists())
