"""
Unit Tests: Social Login (Google & Apple)
=========================================

Tests the POST /api/auth/social-login endpoint.

Strategy:
  - Mock the provider verification functions (verify_google_token,
    verify_apple_token) so tests don't hit real external APIs.
  - Test the full request → response cycle through Django's test client.
  - Verify both "new user" and "existing user" flows.
  - Verify error handling for invalid tokens and bad input.
  - Verify profile auto-creation, notifications_id handling, and
    exact API contract compliance.

Note: We mock the provider functions (not the repository), as instructed
in the task docs.
"""
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.exceptions import UnauthorizedError
from apps.users.models import CustomUser, CustomerProfile, OwnerProfile, UserDevice
from apps.users.tests.test_error_format import _assert_error_envelope


# ---------------------------------------------------------------------------
# Helper constants
# ---------------------------------------------------------------------------

# Path to the provider functions we'll mock (mocked where they're imported)
GOOGLE_VERIFY_PATH = "apps.users.views.verify_google_token"
APPLE_VERIFY_PATH = "apps.users.views.verify_apple_token"

# Fake data returned by mocked provider functions
MOCK_GOOGLE_USER = {"email": "ahmed@gmail.com", "name": "Ahmed Mohamed"}
MOCK_APPLE_USER = {"email": "sara@icloud.com", "name": ""}

# All fields the user object must contain per the API contract
EXPECTED_USER_FIELDS = {
    "id", "email", "full_name", "phone_number", "account_type",
    "is_verified", "profile_image", "date_of_birth", "address", "gender",
}


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
class SocialLoginTests(TestCase):
    """Tests for POST /api/auth/social-login."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("auth-social-login")

    # ==================================================================
    # HAPPY PATH — New Users
    # ==================================================================

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_google_login_new_user(self, mock_verify):
        """First-time Google login should create a new user with 201."""
        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        body = response.json()
        self.assertTrue(body["status"])
        self.assertIn("access", body["data"])
        self.assertIn("refresh", body["data"])
        self.assertTrue(body["data"]["is_new_user"])
        self.assertEqual(body["data"]["user"]["email"], "ahmed@gmail.com")
        self.assertTrue(body["data"]["user"]["is_verified"])

    @patch(APPLE_VERIFY_PATH, return_value=MOCK_APPLE_USER)
    def test_apple_login_new_user(self, mock_verify):
        """First-time Apple login should create a new user with 201."""
        response = self.client.post(
            self.url,
            data={
                "provider": "apple",
                "id_token": "VALID_APPLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        body = response.json()
        self.assertTrue(body["status"])
        self.assertTrue(body["data"]["is_new_user"])
        self.assertEqual(body["data"]["user"]["email"], "sara@icloud.com")
        self.assertTrue(body["data"]["user"]["is_verified"])

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_new_owner_via_social_login(self, mock_verify):
        """Social login with account_type=owner should create an owner user."""
        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "owner",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["data"]["user"]["account_type"], "owner")
        self.assertTrue(body["data"]["user"]["is_verified"])

    # ==================================================================
    # HAPPY PATH — Existing Users
    # ==================================================================

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_google_login_existing_user(self, mock_verify):
        """Second Google login with same email should return 200."""
        CustomUser.objects.create_user(
            email="ahmed@gmail.com",
            full_name="Ahmed Mohamed",
            password="SomePass123!",
            account_type="customer",
            is_verified=True,
        )

        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        body = response.json()
        self.assertTrue(body["status"])
        self.assertFalse(body["data"]["is_new_user"])
        self.assertEqual(body["data"]["user"]["email"], "ahmed@gmail.com")

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_email_password_user_can_social_login(self, mock_verify):
        """User who signed up with email/password can also login via Google."""
        user = CustomUser.objects.create_user(
            email="ahmed@gmail.com",
            full_name="Ahmed Mohamed",
            password="SomePass123!",
            account_type="customer",
        )

        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertFalse(body["data"]["is_new_user"])
        # Original user ID should be preserved
        self.assertEqual(body["data"]["user"]["id"], user.pk)

    # ==================================================================
    # INVALID TOKEN ERRORS
    # ==================================================================

    @patch(
        GOOGLE_VERIFY_PATH,
        side_effect=UnauthorizedError(
            message="Social login failed",
            errors={"provider": ["Invalid access token"]},
        ),
    )
    def test_invalid_google_token(self, mock_verify):
        """Invalid Google token should return 401 with error envelope."""
        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "INVALID_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    @patch(
        APPLE_VERIFY_PATH,
        side_effect=UnauthorizedError(
            message="Social login failed",
            errors={"provider": ["Invalid Apple token"]},
        ),
    )
    def test_invalid_apple_token(self, mock_verify):
        """Invalid Apple token should return 401 with error envelope."""
        response = self.client.post(
            self.url,
            data={
                "provider": "apple",
                "id_token": "INVALID_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    # ==================================================================
    # VALIDATION ERRORS (serializer level)
    # ==================================================================

    def test_missing_provider(self):
        """Request without provider should return 400."""
        response = self.client.post(
            self.url,
            data={"id_token": "SOME_TOKEN_1234567890", "account_type": "customer"},
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("provider", body["errors"])

    def test_missing_id_token(self):
        """Request without id_token should return 400."""
        response = self.client.post(
            self.url,
            data={"provider": "google", "account_type": "customer"},
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_token", body["errors"])

    def test_invalid_provider_value(self):
        """Unsupported provider (e.g. 'facebook') should return 400."""
        response = self.client.post(
            self.url,
            data={
                "provider": "facebook",
                "id_token": "SOME_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("provider", body["errors"])

    def test_invalid_account_type(self):
        """account_type='admin' should be rejected — only customer/owner allowed."""
        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "SOME_TOKEN_1234567890",
                "account_type": "admin",
            },
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("account_type", body["errors"])

    def test_id_token_too_short(self):
        """Token shorter than 10 chars should be rejected by serializer."""
        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "short",
                "account_type": "customer",
            },
            format="json",
        )
        body = _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_token", body["errors"])

    def test_empty_body(self):
        """Empty request body should return 400 with field errors."""
        response = self.client.post(self.url, data={}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    # ==================================================================
    # DEACTIVATED USER
    # ==================================================================

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_social_login_deactivated_user(self, mock_verify):
        """Deactivated user should not be able to login via social auth."""
        CustomUser.objects.create_user(
            email="ahmed@gmail.com",
            full_name="Ahmed Mohamed",
            password="SomePass123!",
            account_type="customer",
            is_active=False,
        )

        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    # ==================================================================
    # NOTIFICATIONS_ID HANDLING
    # ==================================================================

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_device_token_saved_on_new_user(self, mock_verify):
        """FCM token should create a UserDevice record for a new social user."""
        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
                "notifications_id": "fcm_token_abc123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = CustomUser.objects.get(email="ahmed@gmail.com")
        self.assertTrue(
            UserDevice.objects.filter(user=user, fcm_token="fcm_token_abc123").exists(),
            "UserDevice should be created with the provided FCM token",
        )

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_device_token_registered_on_existing_user_login(self, mock_verify):
        """FCM token sent on login should be registered as a UserDevice."""
        user = CustomUser.objects.create_user(
            email="ahmed@gmail.com",
            full_name="Ahmed Mohamed",
            password="SomePass123!",
            account_type="customer",
        )
        # Pre-existing device token for another device
        UserDevice.objects.create(user=user, fcm_token="old_device_token")

        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
                "notifications_id": "new_device_token",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Both devices should now be registered (multi-device support)
        self.assertEqual(UserDevice.objects.filter(user=user).count(), 2)
        self.assertTrue(UserDevice.objects.filter(user=user, fcm_token="new_device_token").exists())

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_existing_devices_not_removed_when_token_omitted(self, mock_verify):
        """Omitting notifications_id should NOT remove existing device tokens."""
        user = CustomUser.objects.create_user(
            email="ahmed@gmail.com",
            full_name="Ahmed Mohamed",
            password="SomePass123!",
            account_type="customer",
        )
        UserDevice.objects.create(user=user, fcm_token="existing_token")

        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            UserDevice.objects.filter(user=user, fcm_token="existing_token").exists(),
            "Existing device token should be preserved when no new token is sent",
        )

    # ==================================================================
    # PROFILE AUTO-CREATION (signal)
    # ==================================================================

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_customer_profile_auto_created(self, mock_verify):
        """New customer via social login should have a CustomerProfile."""
        self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        user = CustomUser.objects.get(email="ahmed@gmail.com")
        self.assertTrue(
            CustomerProfile.objects.filter(user=user).exists(),
            "CustomerProfile should be auto-created by signal",
        )

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_owner_profile_auto_created(self, mock_verify):
        """New owner via social login should have an OwnerProfile."""
        self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "owner",
            },
            format="json",
        )

        user = CustomUser.objects.get(email="ahmed@gmail.com")
        self.assertTrue(
            OwnerProfile.objects.filter(user=user).exists(),
            "OwnerProfile should be auto-created by signal",
        )

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_customer_referral_code_generated(self, mock_verify):
        """Auto-created CustomerProfile should have a non-empty 8-char referral code."""
        self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        user = CustomUser.objects.get(email="ahmed@gmail.com")
        profile = CustomerProfile.objects.get(user=user)
        self.assertTrue(len(profile.referral_code) > 0)
        self.assertEqual(len(profile.referral_code), 8)

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_owner_profile_default_values(self, mock_verify):
        """Auto-created OwnerProfile should have correct defaults."""
        self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "owner",
            },
            format="json",
        )

        user = CustomUser.objects.get(email="ahmed@gmail.com")
        profile = OwnerProfile.objects.get(user=user)
        self.assertEqual(profile.owner_type, "individual")
        self.assertEqual(profile.verification_status, "pending")
        self.assertIsNone(profile.national_id_number)

    # ==================================================================
    # SOCIAL USER PASSWORD HANDLING
    # ==================================================================

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_social_user_has_unusable_password(self, mock_verify):
        """New social users should have unusable password (no email/password login)."""
        self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        user = CustomUser.objects.get(email="ahmed@gmail.com")
        self.assertFalse(user.has_usable_password())

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_social_user_cannot_login_with_password(self, mock_verify):
        """Social user should not be able to login via email/password endpoint."""
        self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        login_url = reverse("auth-login")
        response = self.client.post(
            login_url,
            data={"email": "ahmed@gmail.com", "password": "anything"},
            format="json",
        )
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)

    # ==================================================================
    # EMAIL NORMALIZATION
    # ==================================================================

    @patch(GOOGLE_VERIFY_PATH, return_value={"email": "Ahmed@Gmail.COM", "name": "Ahmed"})
    def test_email_is_case_insensitive(self, mock_verify):
        """Email from provider should be lowercased — no duplicate accounts."""
        CustomUser.objects.create_user(
            email="ahmed@gmail.com",
            full_name="Ahmed",
            password="SomePass123!",
            account_type="customer",
        )

        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["data"]["is_new_user"])
        self.assertEqual(CustomUser.objects.count(), 1)

    @patch(GOOGLE_VERIFY_PATH, return_value={"email": "  user@gmail.com  ", "name": "User"})
    def test_email_whitespace_trimmed(self, mock_verify):
        """Email with leading/trailing whitespace should be trimmed."""
        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CustomUser.objects.filter(email="user@gmail.com").exists())

    # ==================================================================
    # API CONTRACT — Exact Response Shape
    # ==================================================================

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_new_user_response_matches_api_contract(self, mock_verify):
        """New user response must contain exactly the fields specified in API docs."""
        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        body = response.json()

        # Top-level envelope
        self.assertIn("status", body)
        self.assertIn("message", body)
        self.assertIn("data", body)
        self.assertTrue(body["status"])

        # Data fields
        data = body["data"]
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIn("is_new_user", data)
        self.assertIn("user", data)

        # User object — must contain exactly these fields
        user_fields = set(data["user"].keys())
        self.assertEqual(
            user_fields,
            EXPECTED_USER_FIELDS,
            f"User object fields mismatch. Extra: {user_fields - EXPECTED_USER_FIELDS}, "
            f"Missing: {EXPECTED_USER_FIELDS - user_fields}",
        )

    @patch(GOOGLE_VERIFY_PATH, return_value=MOCK_GOOGLE_USER)
    def test_existing_user_response_matches_api_contract(self, mock_verify):
        """Existing user response must match the same contract."""
        CustomUser.objects.create_user(
            email="ahmed@gmail.com",
            full_name="Ahmed Mohamed",
            password="SomePass123!",
            account_type="customer",
        )

        response = self.client.post(
            self.url,
            data={
                "provider": "google",
                "id_token": "VALID_GOOGLE_TOKEN_1234567890",
                "account_type": "customer",
            },
            format="json",
        )

        body = response.json()
        self.assertEqual(body["message"], "Login successful")
        self.assertFalse(body["data"]["is_new_user"])

        user_fields = set(body["data"]["user"].keys())
        self.assertEqual(user_fields, EXPECTED_USER_FIELDS)

    # ==================================================================
    # REFERRAL CODE UNIQUENESS
    # ==================================================================

    def test_two_customers_have_different_referral_codes(self):
        """Two customers should never have the same referral code."""
        user1 = CustomUser.objects.create_user(
            email="user1@test.com", full_name="User One",
            password="ValidPass123!", account_type="customer",
        )
        user2 = CustomUser.objects.create_user(
            email="user2@test.com", full_name="User Two",
            password="ValidPass123!", account_type="customer",
        )

        profile1 = CustomerProfile.objects.get(user=user1)
        profile2 = CustomerProfile.objects.get(user=user2)

        self.assertNotEqual(profile1.referral_code, profile2.referral_code)
        self.assertEqual(len(profile1.referral_code), 8)
        self.assertEqual(len(profile2.referral_code), 8)
