"""
Tests for the TermsAndConditions app.

Coverage:
Public side
- GET  /api/TermsAndConditions/           list TermsAndConditionss

Admin side — TermsAndConditionss
- POST   /api/admin/TermsAndConditions/
- GET    /api/admin/TermsAndConditions/
- GET    /api/admin/TermsAndConditions/{id}/
- PATCH  /api/admin/TermsAndConditions/{id}/
- DELETE /api/admin/TermsAndConditions/{id}/

"""
from __future__ import annotations

from unittest.mock import patch, MagicMock  # noqa: F401
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser
from apps.terms_and_conditions.repositories.terms_and_conditions_repository import TermsAndConditionsRepository
from apps.terms_and_conditions.services.terms_and_conditions_service import TermsAndConditionsService


def _mock_translation_service():
    mock = MagicMock()
    mock.translate_batch.side_effect = lambda texts, _lang: texts  # returns originals
    return mock


def _get_test_TermsAndConditions_service():
    return TermsAndConditionsService(
        repository=TermsAndConditionsRepository(),
        translation=_mock_translation_service(),
    )


_PATCH_TARGET = "apps.terms_and_conditions.views._get_TermsAndConditions_service"


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


def _assert_success(test_case, response, expected_status=status.HTTP_200_OK):
    test_case.assertEqual(response.status_code, expected_status)
    body = response.json()
    test_case.assertTrue(body["status"])
    test_case.assertIn("data", body)
    return body


def _assert_error(test_case, response, expected_status):
    test_case.assertEqual(response.status_code, expected_status)
    body = response.json()
    test_case.assertFalse(body["status"])
    test_case.assertIn("message", body)
    return body


class AdminTermsAndConditionsTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin@example.com")
        self.client = _auth_client(self.admin)
        self.base_url = "/api/admin/termsandconditions/"
        patcher = patch(_PATCH_TARGET, side_effect=_get_test_TermsAndConditions_service)
        self.mock_service = patcher.start()
        self.addCleanup(patcher.stop)

    def _TermsAndConditions_payload(self, title="test title", content="test content"):
        return {
            "title": title,
            "content": content,
        }

    def test_add_TermsAndConditions_returns_201(self):
        response = self.client.post(self.base_url, self._TermsAndConditions_payload())
        body = _assert_success(self, response, status.HTTP_201_CREATED)
        self.assertEqual(body["data"]["title"], "test title")
        self.assertEqual(body["data"]["content"], "test content")

    def test_add_TermsAndConditions_missing_title_returns_400(self):
        payload = {"content": "test content"}
        response = self.client.post(self.base_url, payload)
        _assert_error(self, response, status.HTTP_400_BAD_REQUEST)

    def test_add_TermsAndConditions_missing_content_returns_400(self):
        payload = {"title": "test title"}
        response = self.client.post(self.base_url, payload)
        _assert_error(self, response, status.HTTP_400_BAD_REQUEST)

    def test_list_TermsAndConditionss_returns_200(self):
        self.client.post(self.base_url, self._TermsAndConditions_payload("test title 1", "test content 1"))
        self.client.post(self.base_url, self._TermsAndConditions_payload("test title 2", "test content 2"))
        response = self.client.get(self.base_url)
        body = _assert_success(self, response)
        self.assertEqual(len(body["data"]), 2)

    def test_get_single_TermsAndConditions_returns_200(self):
        post_response = self.client.post(self.base_url, self._TermsAndConditions_payload("test title 1", "test content 1"))
        TermsAndConditions_id = post_response.json()["data"]["id"]
        response = self.client.get(f"{self.base_url}{TermsAndConditions_id}/")
        body = _assert_success(self, response)
        self.assertEqual(body["data"]["id"], TermsAndConditions_id)

    def test_get_nonexistent_TermsAndConditions_returns_404(self):
        response = self.client.get(f"{self.base_url}99999/")
        _assert_error(self, response, status.HTTP_404_NOT_FOUND)

    def test_update_TermsAndConditions_returns_200(self):
        post_response = self.client.post(self.base_url, self._TermsAndConditions_payload("test title 1", "test content 1"))
        TermsAndConditions_id = post_response.json()["data"]["id"]
        response = self.client.patch(f"{self.base_url}{TermsAndConditions_id}/", {"title": "Renamed"})
        body = _assert_success(self, response)
        self.assertEqual(body["data"]["title"], "Renamed")

    def test_non_admin_cannot_create_TermsAndConditions(self):
        customer = _make_user("cust3@example.com", account_type="customer", is_verified=True)
        client = _auth_client(customer)
        response = client.post(self.base_url, self._TermsAndConditions_payload())
        _assert_error(self, response, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_TermsAndConditionss(self):
        unauth = APIClient()
        unauth.defaults["HTTP_DEVICE_TYPE"] = "web"
        response = unauth.get(self.base_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_toggle_active_TermsAndConditions_returns_200(self):
        post_response = self.client.post(self.base_url, self._TermsAndConditions_payload("Terms 1", "Content 1"))
        TermsAndConditions_id = post_response.json()["data"]["id"]
        response = self.client.patch(f"{self.base_url}{TermsAndConditions_id}/toggle-active/")
        body = _assert_success(self, response)
        self.assertEqual(body["data"]["id"], TermsAndConditions_id)
        self.assertEqual(body["data"]["is_active"], False)


class PublicTermsAndConditionsTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin_pub@example.com")
        self.admin_client = _auth_client(self.admin)
        self.client = APIClient()
        self.client.defaults["HTTP_DEVICE_TYPE"] = "web"
        self.base_url = "/api/terms_and_conditions/"
        patcher = patch(_PATCH_TARGET, side_effect=_get_test_TermsAndConditions_service)
        self.mock_service = patcher.start()
        self.addCleanup(patcher.stop)

    def test_list_TermsAndConditionss_returns_200(self):
        self.admin_client.post("/api/admin/termsandconditions/", {"title": "Terms 1", "content": "Content 1"})
        response = self.client.get(self.base_url)
        body = _assert_success(self, response)
        self.assertEqual(len(body["data"]), 1)

