"""
Feature Tests: User Profile (Get & Update)
==========================================

Covers GET and PATCH /api/auth/profile.
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser
from apps.users.tests.test_error_format import _assert_error_envelope

DB_OVERRIDE = override_settings(
    ALLOWED_HOSTS=["*"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
)

EXPECTED_PROFILE_FIELDS = {
    "id", "email", "full_name", "phone_number", "account_type",
    "is_verified", "profile_image", "date_of_birth", "address", "gender",
}


def _make_user(**kwargs):
    return CustomUser.objects.create_user(
        email=kwargs.get("email", "profile@example.com"),
        full_name=kwargs.get("full_name", "Profile User"),
        password=kwargs.get("password", "ValidPass1!"),
        account_type=kwargs.get("account_type", "customer"),
        is_verified=True,
    )


def _auth_client(user):
    client = APIClient()
    access = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    client.defaults["HTTP_DEVICE_TYPE"] = "web"
    return client


@DB_OVERRIDE
class GetProfileTests(TestCase):
    def setUp(self):
        self.url = reverse("auth-profile")

    def test_get_profile_happy_path(self):
        """GET /profile → 200 with the current user's data."""
        user = _make_user()
        client = _auth_client(user)
        response = client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertTrue(body["status"])
        self.assertEqual(body["data"]["email"], "profile@example.com")

    def test_get_profile_returns_expected_fields(self):
        """Profile response contains exactly the documented fields."""
        user = _make_user()
        client = _auth_client(user)
        response = client.get(self.url)

        fields = set(response.json()["data"].keys())
        self.assertEqual(fields, EXPECTED_PROFILE_FIELDS)

    def test_get_profile_unauthenticated_returns_401(self):
        """GET without JWT → 401."""
        response = APIClient().get(self.url)
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)


@DB_OVERRIDE
class UpdateProfileTests(TestCase):
    def setUp(self):
        self.url = reverse("auth-profile")

    def test_update_full_name(self):
        """PATCH full_name → 200 and name is updated."""
        user = _make_user()
        client = _auth_client(user)
        response = client.patch(self.url, data={"full_name": "Updated Name"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.full_name, "Updated Name")

    def test_update_phone_number_valid(self):
        """PATCH phone_number with international format → 200."""
        user = _make_user()
        client = _auth_client(user)
        response = client.patch(self.url, data={"phone_number": "+201234567890"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.phone_number, "+201234567890")

    def test_update_phone_without_plus_returns_400(self):
        """Phone number without '+' prefix → 400."""
        user = _make_user()
        client = _auth_client(user)
        response = client.patch(self.url, data={"phone_number": "01234567890"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_400_BAD_REQUEST)

    def test_update_gender(self):
        """PATCH gender → 200."""
        user = _make_user()
        client = _auth_client(user)
        response = client.patch(self.url, data={"gender": "male"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.gender, "male")

    def test_update_address(self):
        """PATCH address → 200."""
        user = _make_user()
        client = _auth_client(user)
        response = client.patch(self.url, data={"address": "123 Main St, Cairo"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.address, "123 Main St, Cairo")

    def test_partial_update_does_not_clear_other_fields(self):
        """Updating one field should not affect unmentioned fields."""
        user = _make_user()
        user.address = "Original Address"
        user.save()
        client = _auth_client(user)
        client.patch(self.url, data={"full_name": "New Name"}, format="json")

        user.refresh_from_db()
        self.assertEqual(user.address, "Original Address")

    def test_update_unauthenticated_returns_401(self):
        """PATCH without JWT → 401."""
        response = APIClient().patch(self.url, data={"full_name": "X"}, format="json")
        _assert_error_envelope(self, response, status.HTTP_401_UNAUTHORIZED)
