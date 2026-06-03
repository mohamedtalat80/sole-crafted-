"""
Tests for the privacy_policy app.

Public:
- GET  /api/privacy-policy/          list active policies

Admin:
- POST   /api/admin/privacy-policy/
- GET    /api/admin/privacy-policy/
- GET    /api/admin/privacy-policy/{id}/
- PATCH  /api/admin/privacy-policy/{id}/
- DELETE /api/admin/privacy-policy/{id}/
- POST   /api/admin/privacy-policy/{id}/toggle-active/
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.privacy_policy.repositories.privacy_policy_repository import PrivacyPolicyRepository
from apps.privacy_policy.services.privacy_policy_service import PrivacyPolicyService
from apps.users.models import CustomUser

_PATCH_TARGET = "apps.privacy_policy.views._get_privacy_policy_service"


def _mock_translation_service():
    mock = MagicMock()
    mock.translate_batch.side_effect = lambda texts, _lang: texts
    return mock


def _get_test_service():
    return PrivacyPolicyService(
        repository=PrivacyPolicyRepository(),
        translation=_mock_translation_service(),
    )


def _make_user(email, account_type="admin", password="ValidPass1!", **kwargs):
    return CustomUser.objects.create_superuser(
        email=email,
        full_name="Test User",
        password=password,
        account_type=account_type,
        **kwargs,
    )


def _auth_client(user):
    client = APIClient()
    access = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    client.defaults["HTTP_DEVICE_TYPE"] = "web"
    return client


def _assert_success(tc, response, expected_status=status.HTTP_200_OK):
    tc.assertEqual(response.status_code, expected_status)
    body = response.json()
    tc.assertTrue(body["status"])
    tc.assertIn("data", body)
    return body


def _assert_error(tc, response, expected_status):
    tc.assertEqual(response.status_code, expected_status)
    body = response.json()
    tc.assertFalse(body["status"])
    tc.assertIn("message", body)
    return body


class AdminPrivacyPolicyTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin@example.com")
        self.client = _auth_client(self.admin)
        self.base_url = "/api/admin/privacy-policy/"
        patcher = patch(_PATCH_TARGET, side_effect=_get_test_service)
        self.mock_service = patcher.start()
        self.addCleanup(patcher.stop)

    def _payload(self, title="Test title", content="Test content", display_order=None):
        data = {"title": title, "content": content}
        if display_order is not None:
            data["display_order"] = display_order
        return data

    def test_create_returns_201(self):
        response = self.client.post(self.base_url, self._payload(display_order=1))
        body = _assert_success(self, response, status.HTTP_201_CREATED)
        self.assertEqual(body["data"]["title"], "Test title")
        self.assertEqual(body["data"]["content"], "Test content")

    def test_create_missing_title_returns_400(self):
        response = self.client.post(self.base_url, {"content": "test"})
        _assert_error(self, response, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_content_returns_400(self):
        response = self.client.post(self.base_url, {"title": "test"})
        _assert_error(self, response, status.HTTP_400_BAD_REQUEST)

    def test_list_returns_200(self):
        self.client.post(self.base_url, self._payload("title 1", "content 1", display_order=1))
        self.client.post(self.base_url, self._payload("title 2", "content 2", display_order=2))
        response = self.client.get(self.base_url)
        body = _assert_success(self, response)
        self.assertEqual(len(body["data"]["results"]), 2)

    def test_retrieve_returns_200(self):
        created = self.client.post(self.base_url, self._payload(display_order=1)).json()
        pk = created["data"]["id"]
        response = self.client.get(f"{self.base_url}{pk}/")
        body = _assert_success(self, response)
        self.assertEqual(body["data"]["id"], pk)

    def test_retrieve_nonexistent_returns_404(self):
        response = self.client.get(f"{self.base_url}99999/")
        _assert_error(self, response, status.HTTP_404_NOT_FOUND)

    def test_update_returns_200(self):
        created = self.client.post(self.base_url, self._payload(display_order=1)).json()
        pk = created["data"]["id"]
        response = self.client.patch(f"{self.base_url}{pk}/", {"title": "Renamed"})
        body = _assert_success(self, response)
        self.assertEqual(body["data"]["title"], "Renamed")

    def test_delete_returns_200(self):
        created = self.client.post(self.base_url, self._payload(display_order=1)).json()
        pk = created["data"]["id"]
        response = self.client.delete(f"{self.base_url}{pk}/")
        _assert_success(self, response)

    def test_toggle_active_returns_200(self):
        created = self.client.post(self.base_url, self._payload(display_order=1)).json()
        pk = created["data"]["id"]
        response = self.client.post(f"{self.base_url}{pk}/toggle-active/")
        body = _assert_success(self, response)
        self.assertEqual(body["data"]["is_active"], False)

    def test_non_admin_cannot_create(self):
        customer = _make_user("cust@example.com", account_type="customer", is_verified=True)
        client = _auth_client(customer)
        response = client.post(self.base_url, self._payload())
        _assert_error(self, response, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list(self):
        unauth = APIClient()
        unauth.defaults["HTTP_DEVICE_TYPE"] = "web"
        response = unauth.get(self.base_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class PublicPrivacyPolicyTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin_pub@example.com")
        self.admin_client = _auth_client(self.admin)
        self.client = APIClient()
        self.client.defaults["HTTP_DEVICE_TYPE"] = "web"
        self.public_url = "/api/privacy-policy/"
        self.admin_url = "/api/admin/privacy-policy/"
        patcher = patch(_PATCH_TARGET, side_effect=_get_test_service)
        self.mock_service = patcher.start()
        self.addCleanup(patcher.stop)

    def test_list_active_returns_200(self):
        self.admin_client.post(self.admin_url, {"title": "PP 1", "content": "Content 1", "display_order": 1})
        response = self.client.get(self.public_url)
        body = _assert_success(self, response)
        self.assertIn("results", body["data"])
