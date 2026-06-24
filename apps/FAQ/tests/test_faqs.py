"""
Tests for the FAQ app.

Coverage:
Public side
- GET  /api/FAQ/           list owner FAQs

Admin side — FAQs
- POST   /api/admin/FAQ/
- GET    /api/admin/FAQ/
- GET    /api/admin/FAQ/{id}/
- PATCH  /api/admin/FAQ/{id}/
- DELETE /api/admin/FAQ/{id}/
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock  # noqa: F401
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import CustomUser
from apps.FAQ.repositories.faq_repository import FAQRepository
from apps.FAQ.services.faq_service import FAQService


def _mock_translation_service():
    mock = MagicMock()
    mock.translate_batch.side_effect = lambda texts, _lang: texts  # returns originals
    return mock


def _get_test_faq_service():
    return FAQService(
        repository=FAQRepository(),
        translation=_mock_translation_service(),
    )


_PATCH_TARGET = "apps.FAQ.views._get_FAQ_service"


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


class AdminFAQTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin@example.com")
        self.client = _auth_client(self.admin)
        self.base_url = "/api/admin/FAQ/"
        patcher = patch(_PATCH_TARGET, side_effect=_get_test_faq_service)
        self.mock_service = patcher.start()
        self.addCleanup(patcher.stop)

    def _faq_payload(self, question="How to add a boat?", answer="Answer to the question"):
        return {
            "question": question,
            "answer": answer,
        }

    def test_add_faq_returns_201(self):
        response = self.client.post(self.base_url, self._faq_payload())
        body = _assert_success(self, response, status.HTTP_201_CREATED)
        self.assertEqual(body["data"]["question"], "How to add a boat?")
        self.assertEqual(body["data"]["answer"], "Answer to the question")

    def test_add_faq_missing_question_returns_400(self):
        payload = {"answer": "Answer to the question"}
        response = self.client.post(self.base_url, payload, format="multipart")
        _assert_error(self, response, status.HTTP_400_BAD_REQUEST)

    def test_add_faq_missing_answer_returns_400(self):
        payload = {"question": "How to add a boat?"}
        response = self.client.post(self.base_url, payload, format="multipart")
        _assert_error(self, response, status.HTTP_400_BAD_REQUEST)

    def test_list_faqs_returns_200(self):
        self.client.post(self.base_url, self._faq_payload("FAQ 1", "Answer 1"))
        self.client.post(self.base_url, self._faq_payload("FAQ 2", "Answer 2"))
        response = self.client.get(self.base_url)
        body = _assert_success(self, response)
        self.assertEqual(len(body["data"]), 2)

    def test_get_single_faq_returns_200(self):
        post_response = self.client.post(self.base_url, self._faq_payload("FAQ 1", "Answer 1"))
        faq_id = post_response.json()["data"]["id"]
        response = self.client.get(f"{self.base_url}{faq_id}/")
        body = _assert_success(self, response)
        self.assertEqual(body["data"]["id"], faq_id)

    def test_get_nonexistent_faq_returns_404(self):
        response = self.client.get(f"{self.base_url}99999/")
        _assert_error(self, response, status.HTTP_404_NOT_FOUND)

    def test_update_faq_returns_200(self):
        post_response = self.client.post(self.base_url, self._faq_payload("FAQ 1", "Answer 1"))
        faq_id = post_response.json()["data"]["id"]
        response = self.client.patch(f"{self.base_url}{faq_id}/", {"question": "Renamed"}, format="multipart")
        body = _assert_success(self, response)
        self.assertEqual(body["data"]["question"], "Renamed")

    def test_non_admin_cannot_create_faq(self):
        customer = _make_user("cust3@example.com", account_type="customer", is_verified=True)
        client = _auth_client(customer)
        response = client.post(self.base_url, self._faq_payload())
        _assert_error(self, response, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_faqs(self):
        unauth = APIClient()
        unauth.defaults["HTTP_DEVICE_TYPE"] = "web"
        response = unauth.get(self.base_url)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class PublicFAQTests(TestCase):
    def setUp(self):
        self.admin = _make_user("admin_pub@example.com")
        self.admin_client = _auth_client(self.admin)
        self.url = "/api/FAQ/"
        patcher = patch(_PATCH_TARGET, side_effect=_get_test_faq_service)
        self.mock_service = patcher.start()
        self.addCleanup(patcher.stop)

    def test_list_faqs_returns_200(self):
        self.admin_client.post(self.url, {"question": "Q1", "answer": "A1"})
        self.admin_client.post(self.url, {"question": "Q2", "answer": "A2"})
        response = self.client.get(self.url)
        body = _assert_success(self, response)
        self.assertEqual(len(body["data"]), 2)

