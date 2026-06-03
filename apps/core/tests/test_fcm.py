"""
FCM notification integration tests.

What is tested
──────────────
Layer 1 — FcmProvider (apps/core/fcm_provider.py)
  · OAuth2 token acquisition (JWT creation + token-endpoint exchange)
  · Token caching (second call must NOT re-hit the token endpoint)
  · Token refresh after expiry
  · send_to_user fans out one request per device token
  · send_to_user is a no-op when provider is unconfigured (sa_info=None)
  · send_to_user is a no-op when the user has no registered devices
  · FCM HTTP errors are logged, not raised
  · Token-endpoint failures are caught and logged

Layer 2 — BookingNotificationService
  · notify_booking_created / confirmed / cancelled / completed call FcmProvider
  · notify_owner_new_booking calls FcmProvider with owner user

Layer 3 — BoatNotificationService
  · notify_boat_approved  calls FcmProvider AND sends email
  · notify_boat_rejected  calls FcmProvider AND sends email

Layer 4 — Owner NotificationService
  · notify_approved calls FcmProvider AND sends email
  · notify_rejected calls FcmProvider AND sends email

Layer 5 — ReportNotificationService
  · notify_report_status_changed calls FcmProvider
  · Skipped silently when report has no reporter

Layer 6 — Device registration (integration)
  · POST /api/auth/signup with notifications_id creates a UserDevice row
  · POST /api/auth/login  with notifications_id creates / reassigns UserDevice
  · Token reassignment: login with a token that belonged to another user

All external calls (urllib, jwt.encode) are mocked — no network I/O.
"""
from __future__ import annotations

import json
import time
from io import BytesIO
from unittest.mock import MagicMock, patch, call

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.fcm_provider import FcmProvider, _TOKEN_CACHE, _TOKEN_LOCK
from apps.users.models import CustomUser, UserDevice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SA_INFO = {
    "type": "service_account",
    "project_id": "test-project",
    "client_email": "firebase-test@test-project.iam.gserviceaccount.com",
    "private_key": "FAKE_PRIVATE_KEY",
}

_FAKE_ACCESS_TOKEN = "ya29.fake-access-token"


def _make_user(email, account_type="customer", password="ValidPass1!", **kwargs):
    # is_verified defaults to True for tests; callers can override via kwargs
    kwargs.setdefault("is_verified", True)
    return CustomUser.objects.create_user(
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
    client.defaults["HTTP_DEVICE_TYPE"] = "mobile"
    return client


def _mock_token_response(token=_FAKE_ACCESS_TOKEN, expires_in=3600):
    """Return a fake urllib response for the OAuth2 token endpoint."""
    body = json.dumps({"access_token": token, "expires_in": expires_in}).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.status = 200
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _mock_fcm_response(http_status=200):
    """Return a fake urllib response for the FCM send endpoint."""
    resp = MagicMock()
    resp.status = http_status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def _reset_token_cache():
    """Clear the module-level token cache between tests."""
    with _TOKEN_LOCK:
        _TOKEN_CACHE["token"] = None
        _TOKEN_CACHE["expires_at"] = 0.0


# ---------------------------------------------------------------------------
# Layer 1 — FcmProvider unit tests
# ---------------------------------------------------------------------------

class FcmProviderNotConfiguredTest(TestCase):
    """When sa_info is None the provider must be a complete no-op."""

    def test_is_not_configured(self):
        p = FcmProvider(None)
        self.assertFalse(p._is_configured)

    def test_send_to_user_noop_no_sa_info(self):
        p = FcmProvider(None)
        user = MagicMock()
        with patch("urllib.request.urlopen") as mock_open:
            p.send_to_user(user, title="Hi", body="There")
        mock_open.assert_not_called()


class FcmProviderNoDevicesTest(TestCase):
    """send_to_user must skip the FCM call when the user has no tokens."""

    def setUp(self):
        _reset_token_cache()
        self.user = _make_user("nodevice@example.com")

    def test_send_to_user_noop_no_devices(self):
        p = FcmProvider(_SA_INFO)
        with patch("urllib.request.urlopen") as mock_open:
            p.send_to_user(self.user, title="Hi", body="There")
        mock_open.assert_not_called()


class FcmProviderTokenAcquisitionTest(TestCase):
    """OAuth2 token exchange via JWT assertion."""

    def setUp(self):
        _reset_token_cache()
        self.user = _make_user("tokentest@example.com")
        UserDevice.objects.create(user=self.user, fcm_token="device-token-001")

    @patch("jwt.encode", return_value="fake.jwt.assertion")
    @patch("urllib.request.urlopen")
    def test_token_acquired_and_cached(self, mock_open, mock_jwt):
        """First call hits the token endpoint; second call uses the cache."""
        mock_open.side_effect = [
            _mock_token_response(),   # token exchange (first send_to_user)
            _mock_fcm_response(),     # FCM send   (first send_to_user)
            _mock_fcm_response(),     # FCM send   (second send_to_user — cache hit)
        ]

        p = FcmProvider(_SA_INFO)
        p.send_to_user(self.user, title="A", body="B")
        p.send_to_user(self.user, title="C", body="D")

        # 1 token exchange + 2 FCM sends = 3 total urlopen calls
        self.assertEqual(mock_open.call_count, 3)

    @patch("jwt.encode", return_value="fake.jwt.assertion")
    @patch("urllib.request.urlopen")
    def test_token_refreshed_after_expiry(self, mock_open, mock_jwt):
        """Token is re-fetched when the cached one is within 60 s of expiry."""
        mock_open.side_effect = [
            _mock_token_response(),  # first exchange
            _mock_fcm_response(),    # first FCM send
            _mock_token_response(),  # second exchange (cache expired)
            _mock_fcm_response(),    # second FCM send
        ]

        p = FcmProvider(_SA_INFO)

        # First call: populates cache (2 urlopen calls)
        p.send_to_user(self.user, title="A", body="B")
        self.assertEqual(mock_open.call_count, 2)

        # Force cache to appear as if it expires in < 60 s
        with _TOKEN_LOCK:
            _TOKEN_CACHE["expires_at"] = time.time() + 30

        # Second call: must exchange again (2 more urlopen calls)
        p.send_to_user(self.user, title="C", body="D")
        self.assertEqual(mock_open.call_count, 4)

    @patch("jwt.encode", return_value="fake.jwt.assertion")
    @patch("urllib.request.urlopen")
    def test_jwt_payload_contains_required_fields(self, mock_open, mock_jwt):
        """Signed JWT must contain iss, scope, aud, iat, exp."""
        mock_open.side_effect = [_mock_token_response(), _mock_fcm_response()]
        FcmProvider(_SA_INFO).send_to_user(self.user, title="X", body="Y")

        call_args = mock_jwt.call_args
        payload = call_args[0][0]  # first positional arg is the payload dict

        self.assertEqual(payload["iss"], _SA_INFO["client_email"])
        self.assertIn("scope", payload)
        self.assertIn("aud",   payload)
        self.assertIn("iat",   payload)
        self.assertIn("exp",   payload)
        self.assertGreater(payload["exp"], payload["iat"])


class FcmProviderSendTest(TestCase):
    """send_to_user → one FCM request per device token."""

    def setUp(self):
        _reset_token_cache()
        self.user = _make_user("multitok@example.com")
        UserDevice.objects.create(user=self.user, fcm_token="tok-A")
        UserDevice.objects.create(user=self.user, fcm_token="tok-B")

    @patch("jwt.encode", return_value="fake.jwt")
    @patch("urllib.request.urlopen")
    def test_one_fcm_request_per_device(self, mock_open, _):
        mock_open.side_effect = [
            _mock_token_response(),
            _mock_fcm_response(),   # tok-A
            _mock_fcm_response(),   # tok-B
        ]
        FcmProvider(_SA_INFO).send_to_user(
            self.user, title="Hello", body="World",
            data={"booking_id": "42"},
        )
        # 1 token exchange + 2 FCM sends = 3 urlopen calls
        self.assertEqual(mock_open.call_count, 3)

    @patch("jwt.encode", return_value="fake.jwt")
    @patch("urllib.request.urlopen")
    def test_fcm_payload_shape(self, mock_open, _):
        """FCM request body must follow the HTTP v1 message schema."""
        mock_open.side_effect = [_mock_token_response(), _mock_fcm_response()]
        self.user.devices.all().delete()
        UserDevice.objects.create(user=self.user, fcm_token="single-tok")

        FcmProvider(_SA_INFO).send_to_user(
            self.user, title="T", body="B", data={"k": "v"}
        )

        # Find the FCM call (second urlopen call)
        fcm_call = mock_open.call_args_list[1]
        request_obj = fcm_call[0][0]
        payload = json.loads(request_obj.data)

        self.assertIn("message", payload)
        msg = payload["message"]
        self.assertEqual(msg["token"], "single-tok")
        self.assertEqual(msg["notification"]["title"], "T")
        self.assertEqual(msg["notification"]["body"],  "B")
        self.assertEqual(msg["data"]["k"], "v")

    @patch("jwt.encode", return_value="fake.jwt")
    @patch("urllib.request.urlopen")
    def test_fcm_authorization_header(self, mock_open, _):
        """FCM request must carry a Bearer token."""
        mock_open.side_effect = [_mock_token_response(), _mock_fcm_response()]
        self.user.devices.all().delete()
        UserDevice.objects.create(user=self.user, fcm_token="t")

        FcmProvider(_SA_INFO).send_to_user(self.user, title="Hi", body="There")

        fcm_req = mock_open.call_args_list[1][0][0]
        self.assertIn(
            f"Bearer {_FAKE_ACCESS_TOKEN}",
            fcm_req.get_header("Authorization"),
        )

    @patch("jwt.encode", return_value="fake.jwt")
    @patch("urllib.request.urlopen")
    def test_fcm_http_error_logged_not_raised(self, mock_open, _):
        """A 400 from FCM must be logged but must NOT propagate."""
        mock_open.side_effect = [_mock_token_response(), _mock_fcm_response(400)]
        self.user.devices.all().delete()
        UserDevice.objects.create(user=self.user, fcm_token="bad-tok")

        with self.assertLogs("apps.core.fcm_provider", level="WARNING") as cm:
            FcmProvider(_SA_INFO).send_to_user(self.user, title="X", body="Y")

        self.assertTrue(any("400" in line for line in cm.output))

    @patch("jwt.encode", return_value="fake.jwt")
    @patch("urllib.request.urlopen", side_effect=Exception("network down"))
    def test_token_endpoint_failure_logged_not_raised(self, mock_open, _):
        """If the token exchange fails, the error must be caught and logged."""
        self.user.devices.all().delete()
        UserDevice.objects.create(user=self.user, fcm_token="t")

        with self.assertLogs("apps.core.fcm_provider", level="ERROR") as cm:
            FcmProvider(_SA_INFO).send_to_user(self.user, title="X", body="Y")

        self.assertTrue(any("access token" in line.lower() for line in cm.output))


# ---------------------------------------------------------------------------
# Layer 2 — BookingNotificationService
# ---------------------------------------------------------------------------

class BookingNotificationServiceTest(TestCase):

    def _make_booking(self, customer, status="pending", reference_code="REF001",
                      booking_type="trip"):
        booking = MagicMock()
        booking.pk = 1
        booking.customer = customer
        booking.status = status
        booking.reference_code = reference_code
        booking.booking_type = booking_type
        booking.booking_date = "2026-05-01"
        trip = MagicMock()
        trip.name = "Sunset Cruise"
        booking.trip = trip
        booking.rent = None
        return booking

    def setUp(self):
        self.user = _make_user("customer@example.com")
        self.owner = _make_user("owner@example.com", account_type="owner")

    def _make_service(self):
        from apps.bookings.services.booking_notification_service import (
            BookingNotificationService,
        )
        provider = MagicMock(spec=FcmProvider)
        return BookingNotificationService(fcm_provider=provider), provider

    def test_notify_booking_created(self):
        svc, provider = self._make_service()
        booking = self._make_booking(self.user)
        svc.notify_booking_created(booking)
        provider.send_to_user.assert_called_once()
        args, kwargs = provider.send_to_user.call_args
        self.assertEqual(kwargs.get("user") or args[0], self.user)
        self.assertIn("Received", kwargs.get("title") or args[1])

    def test_notify_booking_confirmed(self):
        svc, provider = self._make_service()
        booking = self._make_booking(self.user, status="confirmed")
        svc.notify_booking_confirmed(booking)
        provider.send_to_user.assert_called_once()
        _, kwargs = provider.send_to_user.call_args
        self.assertIn("Confirmed", kwargs["title"])

    def test_notify_booking_cancelled(self):
        svc, provider = self._make_service()
        booking = self._make_booking(self.user, status="cancelled")
        svc.notify_booking_cancelled(booking)
        provider.send_to_user.assert_called_once()

    def test_notify_booking_completed(self):
        svc, provider = self._make_service()
        booking = self._make_booking(self.user, status="completed")
        svc.notify_booking_completed(booking)
        provider.send_to_user.assert_called_once()

    def test_notify_owner_new_booking(self):
        svc, provider = self._make_service()
        booking = self._make_booking(self.user)
        svc.notify_owner_new_booking(self.owner, booking)
        provider.send_to_user.assert_called_once()
        args, kwargs = provider.send_to_user.call_args
        self.assertEqual(kwargs.get("user") or args[0], self.owner)

    def test_data_payload_contains_booking_fields(self):
        svc, provider = self._make_service()
        booking = self._make_booking(self.user, reference_code="ABC123")
        svc.notify_booking_created(booking)
        _, kwargs = provider.send_to_user.call_args
        data = kwargs["data"]
        self.assertEqual(data["reference_code"], "ABC123")
        self.assertIn("booking_id",   data)
        self.assertIn("status",       data)
        self.assertIn("booking_type", data)
        self.assertEqual(data["route"], "booking_id")

    def test_provider_exception_does_not_propagate(self):
        svc, provider = self._make_service()
        provider.send_to_user.side_effect = RuntimeError("FCM down")
        booking = self._make_booking(self.user)
        # Must NOT raise
        svc.notify_booking_created(booking)


# ---------------------------------------------------------------------------
# Layer 3 — BoatNotificationService
# ---------------------------------------------------------------------------

class BoatNotificationServiceTest(TestCase):

    def setUp(self):
        self.user = _make_user("boatowner@example.com", account_type="owner")

    def _make_service(self):
        from apps.boats.services.notification_service import BoatNotificationService
        provider = MagicMock(spec=FcmProvider)
        return BoatNotificationService(fcm_provider=provider), provider

    @patch("apps.boats.services.notification_service.send_mail")
    def test_notify_boat_approved_sends_push_and_email(self, mock_mail):
        svc, provider = self._make_service()
        svc.notify_boat_approved(self.user, "Sea Breeze")
        provider.send_to_user.assert_called_once()
        mock_mail.assert_called_once()

    @patch("apps.boats.services.notification_service.send_mail")
    def test_notify_boat_approved_push_title(self, _):
        svc, provider = self._make_service()
        svc.notify_boat_approved(self.user, "Sea Breeze")
        _, kwargs = provider.send_to_user.call_args
        self.assertIn("Approved", kwargs["title"])

    @patch("apps.boats.services.notification_service.send_mail")
    def test_notify_boat_rejected_sends_push_and_email(self, mock_mail):
        svc, provider = self._make_service()
        svc.notify_boat_rejected(self.user, "Sea Breeze", "Missing documents")
        provider.send_to_user.assert_called_once()
        mock_mail.assert_called_once()

    @patch("apps.boats.services.notification_service.send_mail")
    def test_notify_boat_rejected_body_contains_reason(self, _):
        svc, provider = self._make_service()
        svc.notify_boat_rejected(self.user, "Sea Breeze", "Bad photos")
        _, kwargs = provider.send_to_user.call_args
        self.assertIn("Bad photos", kwargs["body"])

    @patch("apps.boats.services.notification_service.send_mail")
    def test_push_failure_does_not_block_email(self, mock_mail):
        svc, provider = self._make_service()
        provider.send_to_user.side_effect = RuntimeError("FCM down")
        svc.notify_boat_approved(self.user, "Boat X")
        mock_mail.assert_called_once()


# ---------------------------------------------------------------------------
# Layer 4 — Owner NotificationService
# ---------------------------------------------------------------------------

class OwnerNotificationServiceTest(TestCase):

    def setUp(self):
        self.user = _make_user("ownernotif@example.com", account_type="owner")

    def _make_service(self):
        from apps.owner.services.notification_service import NotificationService
        provider = MagicMock(spec=FcmProvider)
        return NotificationService(fcm_provider=provider), provider

    @patch("apps.owner.services.notification_service.send_mail")
    def test_notify_approved_push_and_email(self, mock_mail):
        svc, provider = self._make_service()
        svc.notify_approved(self.user, "2027-01-01")
        provider.send_to_user.assert_called_once()
        mock_mail.assert_called_once()

    @patch("apps.owner.services.notification_service.send_mail")
    def test_notify_approved_title(self, _):
        svc, provider = self._make_service()
        svc.notify_approved(self.user, "2027-01-01")
        _, kwargs = provider.send_to_user.call_args
        self.assertIn("Approved", kwargs["title"])

    @patch("apps.owner.services.notification_service.send_mail")
    def test_notify_rejected_push_and_email(self, mock_mail):
        svc, provider = self._make_service()
        svc.notify_rejected(self.user, "Bad docs", can_renew_at="2026-06-01")
        provider.send_to_user.assert_called_once()
        mock_mail.assert_called_once()

    @patch("apps.owner.services.notification_service.send_mail")
    def test_notify_rejected_body_contains_reason(self, _):
        svc, provider = self._make_service()
        svc.notify_rejected(self.user, "Missing tax card", can_renew_at=None)
        _, kwargs = provider.send_to_user.call_args
        self.assertIn("Missing tax card", kwargs["body"])

    @patch("apps.owner.services.notification_service.send_mail")
    def test_notify_rejected_no_renew_date(self, mock_mail):
        """can_renew_at=None must not crash."""
        svc, provider = self._make_service()
        svc.notify_rejected(self.user, "Reason", can_renew_at=None)
        mock_mail.assert_called_once()


# ---------------------------------------------------------------------------
# Layer 5 — ReportNotificationService
# ---------------------------------------------------------------------------

class ReportNotificationServiceTest(TestCase):

    def _make_service(self):
        from apps.reports.services.report_notification_service import (
            ReportNotificationService,
        )
        provider = MagicMock(spec=FcmProvider)
        return ReportNotificationService(fcm_provider=provider), provider

    def _make_report(self, reporter, report_type="system"):
        from apps.reports.models import SystemReport, BookingReport
        report = MagicMock(spec=SystemReport if report_type == "system" else BookingReport)
        report.pk = 7
        report.reporter = reporter
        report.title = "Broken feature"
        report.status = "resolved"
        return report

    def setUp(self):
        self.user = _make_user("reporter@example.com")

    def test_notify_report_status_changed(self):
        svc, provider = self._make_service()
        report = self._make_report(self.user)
        svc.notify_report_status_changed(report)
        provider.send_to_user.assert_called_once()

    def test_notify_skipped_when_no_reporter(self):
        svc, provider = self._make_service()
        report = self._make_report(None)
        svc.notify_report_status_changed(report)
        provider.send_to_user.assert_not_called()

    def test_data_payload_contains_report_fields(self):
        svc, provider = self._make_service()
        report = self._make_report(self.user)
        svc.notify_report_status_changed(report)
        _, kwargs = provider.send_to_user.call_args
        data = kwargs["data"]
        self.assertIn("report_id",   data)
        self.assertIn("report_type", data)
        self.assertIn("status",      data)


# ---------------------------------------------------------------------------
# Layer 6 — Device registration (HTTP integration)
# ---------------------------------------------------------------------------

class DeviceRegistrationTest(TestCase):
    """
    Verify the FCM token is persisted in UserDevice when supplied at
    signup or login. No actual FCM calls are made in this layer.
    """

    def setUp(self):
        self.client = APIClient()
        self.client.defaults["HTTP_DEVICE_TYPE"] = "mobile"

    def test_signup_with_notifications_id_creates_device(self):
        payload = {
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "StrongPass1!",
            "account_type": "customer",
            "notifications_id": "fcm-signup-token",
        }
        # Email verification code must be pre-verified for signup to work
        from apps.users.models import EmailVerification
        EmailVerification.objects.create(
            email="newuser@example.com",
            code="000000",
            is_verified=True,
        )

        response = self.client.post("/api/auth/signup", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = CustomUser.objects.get(email="newuser@example.com")
        self.assertTrue(
            UserDevice.objects.filter(user=user, fcm_token="fcm-signup-token").exists()
        )

    def test_login_with_notifications_id_creates_device(self):
        user = _make_user("loginuser@example.com", is_verified=True, password="Pass1234!")
        payload = {
            "email": "loginuser@example.com",
            "password": "Pass1234!",
            "notifications_id": "fcm-login-token",
        }
        response = self.client.post("/api/auth/login", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            UserDevice.objects.filter(user=user, fcm_token="fcm-login-token").exists()
        )

    def test_login_without_notifications_id_does_not_create_device(self):
        user = _make_user("notoken@example.com", is_verified=True, password="Pass1234!")
        payload = {
            "email": "notoken@example.com",
            "password": "Pass1234!",
        }
        response = self.client.post("/api/auth/login", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(UserDevice.objects.filter(user=user).count(), 0)

    def test_token_reassigned_on_new_owner_login(self):
        """
        A token that belonged to user A must be moved to user B when B logs in
        with that token. (Simulates selling a phone.)
        """
        user_a = _make_user("usera@example.com", is_verified=True, password="Pass1234!")
        user_b = _make_user("userb@example.com", is_verified=True, password="Pass5678!")
        token = "shared-device-token"

        # user_a registers the token first (via login)
        self.client.post(
            "/api/auth/login",
            {"email": "usera@example.com", "password": "Pass1234!", "notifications_id": token},
            format="json",
        )
        self.assertTrue(UserDevice.objects.filter(user=user_a, fcm_token=token).exists())

        # user_b logs in with the SAME token → it must be reassigned
        self.client.post(
            "/api/auth/login",
            {"email": "userb@example.com", "password": "Pass5678!", "notifications_id": token},
            format="json",
        )
        self.assertFalse(UserDevice.objects.filter(user=user_a, fcm_token=token).exists())
        self.assertTrue(UserDevice.objects.filter(user=user_b, fcm_token=token).exists())

    def test_notification_ids_returned_in_profile_response(self):
        """GET /api/auth/profile must include the user's registered FCM tokens."""
        user = _make_user("profileuser@example.com")
        UserDevice.objects.create(user=user, fcm_token="profile-tok-1")
        UserDevice.objects.create(user=user, fcm_token="profile-tok-2")

        client = _auth_client(user)
        response = client.get("/api/auth/profile")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        # ProfileView returns UserProfileSerializer directly under data (not nested under "user")
        notification_ids = body["data"]["notification_ids"]
        self.assertIn("profile-tok-1", notification_ids)
        self.assertIn("profile-tok-2", notification_ids)
