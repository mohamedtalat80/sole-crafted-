"""
Auth views for the users app.

Design (SRP / DIP):
- Views handle ONLY HTTP concerns: deserialise input, call service, serialise output.
- All business logic is delegated to UserService (injected via _get_service()).
- _get_service() is a factory method — makes the DI point explicit and testable.
"""
from __future__ import annotations

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view, OpenApiExample
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

from django.conf import settings as django_settings

from apps.core.exceptions import ApplicationError, UnauthorizedError
from apps.core.pagination import PaginationMixin
from apps.core.permissions import IsAdminAccount
from apps.core.responses import error_response, success_response
from apps.users.repositories.user_repository import UserRepository
from apps.users.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordConfirmSerializer,
    RefreshTokenSerializer,
    RequestChangeEmailSerializer,
    SetNewPasswordSerializer,
    SignUpSerializer,
    SocialLoginSerializer,
    UpdateProfileSerializer,
    UserProfileSerializer,
    VerifyChangeEmailSerializer,
    VerifyEmailCodeSerializer,
    ForgotPasswordSerializer,
    VerifyResetCodeSerializer,
    SetFcmTokenSerializer,
    SendVerificationCodeSerializer,
)

from apps.users.services.social_providers import verify_apple_token, verify_google_token
from apps.users.services.user_service import UserService

from apps.core.throttles import (
    LoginThrottle,
    PasswordResetThrottle,
    SendVerificationEmailThrottle,
    SetNewPasswordThrottle,
    SignUpThrottle,
    SocialLoginThrottle,    

)
# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------

def _set_auth_cookies(response, *, access_token: str | None = None, refresh_token: str | None = None) -> None:
    """
    Attach HttpOnly JWT cookies to *response*.

    ``secure`` is True in production (DEBUG=False) and False in development
    so local testing without HTTPS still works.

    SameSite=Lax prevents the browser from sending these cookies on
    cross-origin requests initiated by third-party sites, which is the
    primary CSRF defence. Our HybridJWTAuthentication class adds an
    explicit CSRF token check on top for defence-in-depth.
    """
    jwt_cfg = django_settings.SIMPLE_JWT
    secure = not django_settings.DEBUG

    if access_token is not None:
        max_age = int(jwt_cfg["ACCESS_TOKEN_LIFETIME"].total_seconds())
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=max_age,
            httponly=True,
            secure=secure,
            samesite="Lax",
            path="/",
        )

    if refresh_token is not None:
        max_age = int(jwt_cfg["REFRESH_TOKEN_LIFETIME"].total_seconds())
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=max_age,
            httponly=True,
            secure=secure,
            samesite="Lax",
            path="/",
        )


def _clear_auth_cookies(response) -> None:
    """Remove JWT cookies (called on logout)."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


# ---------------------------------------------------------------------------
# Dependency factory (Dependency Inversion entry point)
# ---------------------------------------------------------------------------

def _get_user_service() -> UserService:
    """
    Factory that wires the concrete repository into the service.

    Replace UserRepository() with any IUserRepository implementation
    (mock, cached, remote) without touching view code.
    """
    return UserService(user_repository=UserRepository())


# ---------------------------------------------------------------------------
# Sign Up
# ---------------------------------------------------------------------------

@extend_schema(tags=["Authentication"])
class SignUpView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [SignUpThrottle]
    @extend_schema(
        operation_id="auth_signup",
        summary="Register a new account",
        auth=[],
        request=SignUpSerializer,
        responses={
            201: OpenApiResponse(description="Account created successfully"),
            400: OpenApiResponse(description="Validation failed"),
            409: OpenApiResponse(description="Email already registered"),
        },
        examples=[
            OpenApiExample(
                "Sign Up Request",
                value={
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "password": "StrongPassword123!",
                    "notifications_id": "fcm_token_xyz"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Sign Up Response — Customer",
                value={
                    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "user": {
                        "full_name": "John Doe",
                        "email": "user@example.com",
                        "phone_number": None,
                        "profile_image": None,
                        "notification_ids": ["fcm_token_xyz"],
                        "is_verified": True,
                        "is_banned": False,
                        "nationality": None,
                        "address": None,
                        "account_type": "customer",
                        "specific_data": {
                            "date_of_birth": None,
                            "gender": None,
                        },
                    },
                },
                response_only=True,
                status_codes=["201"],
            )
        ]
    )
    def post(self, request: Request):
        serializer = SignUpSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        service = _get_user_service()

        user = service.register(
            email=data["email"],
            full_name=data["full_name"],
            password=data["password"],
            notifications_id=data.get("notifications_id"),
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = success_response(
            data={
                "access": access_token,
                "refresh": refresh_token,
                "user": UserProfileSerializer(user).data,
            },
            message="Account created successfully",
            status_code=status.HTTP_201_CREATED,
        )
        _set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)
        return response


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@extend_schema(tags=["Authentication"])
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]
    @extend_schema(
        operation_id="auth_login",
        summary="Login with email and password",
        auth=[],
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            401: OpenApiResponse(description="Invalid credentials"),
        },
        examples=[
            OpenApiExample(
                "Login Request",
                value={
                    "email": "user@example.com",
                    "password": "StrongPassword123!",
                    "notifications_id": "fcm_token_xyz"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Login Response — Customer",
                value={
                    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "user": {
                        "full_name": "John Doe",
                        "email": "user@example.com",
                        "phone_number": "+201001234567",
                        "profile_image": "http://example.com/media/users/profile_images/photo.jpg",
                        "notification_ids": ["fcm_token_xyz"],
                        "is_verified": True,
                        "is_banned": False,
                        "nationality": "Egyptian",
                        "address": "123 Main St, Cairo",
                        "account_type": "customer",
                        "specific_data": {
                            "date_of_birth": "1990-01-15",
                            "gender": "male",
                        },
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ]
    )
    def post(self, request: Request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        service = _get_user_service()

        user = service.login(
            email=data["email"],
            password=data["password"],
            notifications_id=data.get("notifications_id"),
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Tokens are returned in the body (mobile) AND set as HttpOnly cookies
        # (web). Both transports remain usable simultaneously.
        response = success_response(
            data={
                "access": access_token,
                "refresh": refresh_token,
                "user": UserProfileSerializer(user).data,
            },
            message="Login successful",
        )
        _set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)
        return response


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        operation_id="auth_logout",
        summary="Logout and blacklist the refresh token",
        request=LogoutSerializer,
        responses={
            200: OpenApiResponse(description="Logged out successfully"),
            400: OpenApiResponse(description="Invalid token"),
        },
        examples=[
            OpenApiExample(
                "Logout Example",
                value={
                    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI..."
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        # Web clients send the refresh token in the HttpOnly cookie;
        # mobile clients send it in the request body. Accept either.
        refresh_value = request.data.get("refresh") or request.COOKIES.get("refresh_token")

        if not refresh_value:
            return error_response(
                message="Validation failed",
                errors={"refresh": ["This field is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_value)
            token.blacklist()
        except TokenError as exc:
            return error_response(
                message="Logout failed",
                errors={"refresh": [str(exc)]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        response = success_response(data=None, message="Logged out successfully")
        _clear_auth_cookies(response)
        return response


# ---------------------------------------------------------------------------
# Logout All Devices
# ---------------------------------------------------------------------------

@extend_schema(tags=["Authentication"])
class LogoutAllDevicesView(APIView):
    """
    Blacklist every outstanding refresh token belonging to the authenticated user.

    After this call every active session on every device is immediately
    invalidated — clients will need to log in again.
    No request body is required; the user is identified from the JWT
    access token in the Authorization header.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="auth_logout_all_devices",
        summary="Logout from all devices",
        description=(
            "Blacklists all outstanding refresh tokens for the authenticated user. "
            "Every device will need to re-authenticate after this call."
        ),
        request=None,
        responses={
            200: OpenApiResponse(description="Logged out from all devices successfully"),
        },
        examples=[
            OpenApiExample(
                "Logout All Devices Response",
                value={"status": True, "message": "Logged out from all devices successfully", "data": {"sessions_revoked": 3}},
                response_only=True, status_codes=["200"],
            ),
        ],
    )
    def post(self, request: Request):
        try:
            service = _get_user_service()
            count = service.logout_all_devices(request.user)
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )
        return success_response(
            data={"sessions_revoked": count},
            message="Logged out from all devices successfully",
        )


# ---------------------------------------------------------------------------
# Refresh Token
# ---------------------------------------------------------------------------

@extend_schema(tags=["Authentication"])
class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auth_refresh",
        summary="Refresh the access token",
        auth=[],
        request=RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(description="Access token refreshed successfully"),
            401: OpenApiResponse(description="Invalid or expired refresh token"),
        },
        examples=[
            OpenApiExample(
                "Refresh Token Request",
                value={"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
                request_only=True,
            ),
            OpenApiExample(
                "Refresh Token Response",
                value={
                    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "user": {
                        "full_name": "John Doe",
                        "email": "user@example.com",
                        "phone_number": "+201001234567",
                        "profile_image": "http://example.com/media/users/profile_images/photo.jpg",
                        "notification_ids": ["fcm_token_xyz"],
                        "is_verified": True,
                        "is_banned": False,
                        "nationality": "Egyptian",
                        "address": "123 Main St, Cairo",
                        "account_type": "customer",
                        "specific_data": {
                            "date_of_birth": "1990-01-15",
                            "gender": "male",
                        },
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ]
    )
    def post(self, request: Request):
        # Web clients carry the refresh token in the HttpOnly cookie;
        # mobile clients send it in the request body.
        refresh_from_body = request.data.get("refresh")
        refresh_from_cookie = request.COOKIES.get("refresh_token")
        refresh_value = refresh_from_body or refresh_from_cookie

        if not refresh_value:
            return error_response(
                message="Validation failed",
                errors={"refresh": ["This field is required."]},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            old_token = RefreshToken(refresh_value)
            new_access = str(old_token.access_token)

            user_id = old_token.payload.get("user_id")
            service = _get_user_service()
            user = service.get_by_id(user_id)

        except TokenError:
            return error_response(
                message="Invalid or expired refresh token",
                errors={"refresh": ["Token has expired. Please login again"]},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )

        response = success_response(
            data={
                "access": new_access,
                "user": UserProfileSerializer(user).data,
            },
            message="Access token refreshed successfully",
        )
        # Update the access_token cookie for web clients so they stay
        # authenticated without JavaScript touching the token.
        if refresh_from_cookie:
            _set_auth_cookies(response, access_token=new_access)
        return response


# ---------------------------------------------------------------------------
# Social Login (Google / Apple)
# ---------------------------------------------------------------------------

# TODO: Add rate limiting to prevent brute-force and token enumeration attacks.
#   Example: throttle_classes = [AnonRateThrottle] with scope 'social_login'
#   Configure in settings: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {'social_login': '10/min'}
@extend_schema(tags=["Authentication"])
class SocialLoginView(APIView):
    """
    Login or register via Google / Apple access token.

    Flow:
      1. Mobile app authenticates with Google/Apple SDK → gets a token
      2. Mobile sends that token here
      3. We verify it with the provider's servers
      4. If user exists → login. If not → create account (auto-verified)
      5. Return JWT tokens + user data + is_new_user flag
    """
    permission_classes = [AllowAny]
    throttle_classes = [SocialLoginThrottle]
    @extend_schema(
        operation_id="auth_social_login",
        summary="Login or register via social provider",
        auth=[],
        request=SocialLoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful"),
            201: OpenApiResponse(description="New account created via social login"),
            401: OpenApiResponse(description="Invalid social token"),
        },
        examples=[
            OpenApiExample(
                "Social Login Request",
                value={
                    "provider": "google",
                    "id_token": "eyJhbGciOiJSUzI1NiIs...",
                    "notifications_id": "fcm_token_xyz"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Social Login Response",
                value={
                    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "is_new_user": False,
                    "user": {
                        "full_name": "John Doe",
                        "email": "user@example.com",
                        "phone_number": None,
                        "profile_image": None,
                        "notification_ids": ["fcm_token_xyz"],
                        "is_verified": True,
                        "is_banned": False,
                        "nationality": None,
                        "address": None,
                        "account_type": "customer",
                        "specific_data": {
                            "date_of_birth": None,
                            "gender": None,
                        },
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ]
    )
    def post(self, request: Request):
        serializer = SocialLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        provider = data["provider"]

        # Verify the token with the provider.
        # These functions raise UnauthorizedError on expected failures.
        # Wrap in try/except to catch unexpected errors (network timeout, etc.).
        try:
            if provider == "google":
                social_data = verify_google_token(data["id_token"])
            else:  # apple
                social_data = verify_apple_token(data["id_token"])
        except UnauthorizedError:
            raise
        except Exception:
            logger.exception("Unexpected error verifying %s token", provider)
            raise UnauthorizedError(
                message="Authentication failed",
                errors={"id_token": ["Could not verify token with provider. Please try again."]},
            )

        # Get or create the user
        service = _get_user_service()
        user, is_new = service.social_login(
            provider=provider,
            email=social_data["email"],
            full_name=social_data.get("name", ""),
            notifications_id=data.get("notifications_id"),
        )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        response_status = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
        message = "Account created successfully" if is_new else "Login successful"

        return success_response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserProfileSerializer(user).data,
                "is_new_user": is_new,
            },
            message=message,
            status_code=response_status,
        )


# ---------------------------------------------------------------------------
# Profile (current user)
# ---------------------------------------------------------------------------

@extend_schema(tags=["Profile"])
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="profile_get",
        summary="Get current user profile",
        responses={200: UserProfileSerializer},
        examples=[
            OpenApiExample(
                "Profile Response — Customer",
                value={
                    "full_name": "John Doe",
                    "email": "user@example.com",
                    "phone_number": "+201001234567",
                    "profile_image": "http://example.com/media/users/profile_images/photo.jpg",
                    "notification_ids": ["fcm_token_phone", "fcm_token_tablet"],
                    "is_verified": True,
                    "is_banned": False,
                    "nationality": "Egyptian",
                    "address": "123 Main St, Cairo",
                    "account_type": "customer",
                    "specific_data": {
                        "date_of_birth": "1990-01-15",
                        "gender": "male",
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
            
        ],
    )
    def get(self, request: Request):
        return success_response(
            data=UserProfileSerializer(request.user).data,
            message="Profile retrieved successfully",
        )

    @extend_schema(
        operation_id="profile_update",
        summary="Update current user profile",
        request=UpdateProfileSerializer,
        responses={200: UserProfileSerializer},
        examples=[
            OpenApiExample(
                "Update Profile Request",
                value={
                    "full_name": "John Doe Updated",
                    "phone_number": "+201001234567",
                    "nationality": "Egyptian",
                    "address": "123 Main St, Cairo",
                    "date_of_birth": "1990-01-15",
                    "gender": "male",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Update Profile Response",
                value={
                    "full_name": "John Doe Updated",
                    "email": "user@example.com",
                    "phone_number": "+201001234567",
                    "profile_image": None,
                    "notification_ids": ["fcm_token_xyz"],
                    "is_verified": True,
                    "is_banned": False,
                    "nationality": "Egyptian",
                    "address": "123 Main St, Cairo",
                    "account_type": "customer",
                    "specific_data": {
                        "date_of_birth": "1990-01-15",
                        "gender": "male",
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ]
    )
    def patch(self, request: Request):
        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        service = _get_user_service()
        updated_user = service.update_profile(request.user, **serializer.validated_data)

        return success_response(
            data=UserProfileSerializer(updated_user).data,
            message="Profile updated successfully",
        )



# ---------------------------------------------------------------------------
# Send Verification Code
# ---------------------------------------------------------------------------

@extend_schema(tags=["Authentication"])
class SendVerificationCodeView(APIView):
    """
    Send a 6-digit verification code to the given email.
    Used during signup to verify email ownership before account creation.
    """
    permission_classes = [AllowAny]
    throttle_classes = [SendVerificationEmailThrottle]
    @extend_schema(
        operation_id="auth_send_verification_code",
        summary="Send verification code to email",
        auth=[],
        request=SendVerificationCodeSerializer,
        responses={
            200: OpenApiResponse(description="Verification code sent successfully"),
            400: OpenApiResponse(description="Validation failed or email already registered"),
            429: OpenApiResponse(description="Too many requests - code already sent recently"),
        },
        examples=[
            OpenApiExample(
                "Send Verification Code Request",
                value={"email": "user@example.com"},
                request_only=True
            ),
            OpenApiExample(
                "Send Verification Code Response",
                value={
                    "status": True,
                    "message": "Verification code sent to your email",
                    "data": {
                        "email": "user@example.com",
                        "expires_in": 900
                    }
                },
                response_only=True,
                status_codes=["200"],
            ),
        ]
    )
    def post(self, request: Request):
        serializer = SendVerificationCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        service = _get_user_service()
        try:
            data = service.send_verification_code(email=serializer.validated_data["email"])
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )

        return success_response(
            data=data,
            message="Verification code sent to your email",
        )


# ---------------------------------------------------------------------------
# Verify Email Code
# ---------------------------------------------------------------------------

@extend_schema(tags=["Authentication"])
class VerifyEmailCodeView(APIView):
    """
    Verify the 6-digit code sent to the user's email.
    On success, the email is marked verified and signup can proceed.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auth_verify_email_code",
        summary="Verify email with 6-digit code",
        auth=[],
        request=VerifyEmailCodeSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully"),
            400: OpenApiResponse(description="Invalid or expired code"),
        },
        examples=[
            OpenApiExample(
                "Verify Email Code Example",
                value={
                    "email": "user@example.com",
                    "verification_code": "123456"
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        serializer = VerifyEmailCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        service = _get_user_service()
        data = service.verify_email_code(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["verification_code"],
        )

        return success_response(
            data=data,
            message="Email verified successfully. You can now complete your registration.",
        )


# ---------------------------------------------------------------------------
# Account Lifecycle — Delete & Deactivate
# ---------------------------------------------------------------------------

@extend_schema(tags=["Account"])
class AccountView(APIView):
    """
    DELETE — Permanently delete the account (PII anonymised immediately).
    POST   — Deactivate for 60 days; auto-purged after the window expires.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="account_delete",
        summary="Permanently delete account",
        description=(
            "Immediately anonymises all personal data. The account ID and "
            "any historical records (bookings, etc.) are preserved in the "
            "database for data integrity. The email address is freed so the "
            "user can register again with a brand-new account."
        ),
        request=PasswordConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Account deleted successfully"),
            401: OpenApiResponse(description="Incorrect password"),
            403: OpenApiResponse(description="Admin accounts cannot be deleted via API"),
        },
        examples=[
            OpenApiExample(
                "Delete Account Example",
                value={
                    "password": "StrongPassword123!"
                },
                request_only=True
            )
        ]
    )
    def delete(self, request: Request):
        serializer = PasswordConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            service = _get_user_service()
            service.delete_account(request.user, password=serializer.validated_data["password"])
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=None,
            message="Your account has been permanently deleted.",
        )

    @extend_schema(
        operation_id="account_deactivate",
        summary="Deactivate account for 60 days",
        description=(
            "Deactivates the account immediately. If not reactivated within "
            "60 days the account will be permanently purged automatically."
        ),
        request=PasswordConfirmSerializer,
        responses={
            200: OpenApiResponse(description="Account deactivated successfully"),
            400: OpenApiResponse(description="Account already deactivated"),
            401: OpenApiResponse(description="Incorrect password"),
            403: OpenApiResponse(description="Admin accounts cannot be deactivated via API"),
        },
        examples=[
            OpenApiExample(
                "Deactivate Account Example",
                value={
                    "password": "StrongPassword123!"
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        serializer = PasswordConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            service = _get_user_service()
            service.deactivate_account(request.user, password=serializer.validated_data["password"])
        except ApplicationError as exc:
            return error_response(message=exc.message, errors=exc.errors, status_code=exc.status_code)
        return success_response(
            data=None,
            message=(
                "Your account has been deactivated. "
                "It will be permanently deleted after 60 days."
            ),
        )


# ---------------------------------------------------------------------------
# Forgot Password
# ---------------------------------------------------------------------------

@extend_schema(tags=["Password Reset"])
class ForgotPasswordView(APIView):
    """
    Step 1 of the password reset flow.

    Sends a 6-digit code to the email. Always returns 200 to prevent
    email enumeration — the code is only sent when the account exists.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]
    @extend_schema(
        tags=["Password Reset"],
        operation_id="auth_forgot_password",
        summary="Request a password reset code",
        auth=[],
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Reset code sent (if account exists)"),
            400: OpenApiResponse(description="Validation error"),
        },
        examples=[
            OpenApiExample(
                "Forgot Password Example",
                value={
                    "email": "user@example.com"
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        service = _get_user_service()
        data = service.forgot_password(serializer.validated_data["email"])

        return success_response(
            data=data,
            message="If this email is registered you will receive a reset code shortly.",
        )


# ---------------------------------------------------------------------------
# Verify Reset Code
# ---------------------------------------------------------------------------

@extend_schema(tags=["Password Reset"])
class VerifyResetCodeView(APIView):
    """Step 2 — confirms the 6-digit code is valid before allowing a password change."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Password Reset"],
        operation_id="auth_verify_reset_code",
        summary="Verify password reset code",
        auth=[],
        request=VerifyResetCodeSerializer,
        responses={
            200: OpenApiResponse(description="Code verified — proceed to reset"),
            400: OpenApiResponse(description="Invalid or expired code"),
        },
        examples=[
            OpenApiExample(
                "Verify Reset Code Example",
                value={
                    "email": "user@example.com",
                    "code": "123456"
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        serializer = VerifyResetCodeSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        service = _get_user_service()
        data = service.verify_reset_code(
            email=serializer.validated_data["email"],
            code=serializer.validated_data["code"],
        )

        return success_response(
            data=data,
            message="Code verified. You may now set a new password.",
        )


# ---------------------------------------------------------------------------
# Set New Password (step 3 of forgot-password flow)
# ---------------------------------------------------------------------------

@extend_schema(tags=["Password Reset"])
class SetNewPasswordView(APIView):
    """
    Step 3 of the forgot-password flow.

    Sets a new password after the user has verified their identity via
    forgot-password → verify-reset-code. No current password required.
    Use this ONLY after completing verify-reset-code (step 2).
    """
    permission_classes = [AllowAny]
    throttle_classes = [SetNewPasswordThrottle]
    @extend_schema(
        tags=["Password Reset"],
        operation_id="auth_set_new_password",
        summary="Set new password after code verification (forgot-password step 3)",
        auth=[],
        request=SetNewPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successfully"),
            400: OpenApiResponse(description="Validation error or code not verified"),
            404: OpenApiResponse(description="No active account found"),
        },
        examples=[
            OpenApiExample(
                "Set New Password Example",
                value={
                    "email": "user@example.com",
                    "new_password": "NewStrongPassword123!"
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        serializer = SetNewPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        service = _get_user_service()
        service.set_new_password(
            email=serializer.validated_data["email"],
            new_password=serializer.validated_data["new_password"],
        )

        return success_response(
            data=None,
            message="Password reset successfully. You can now log in with your new password.",
        )


# ---------------------------------------------------------------------------
# Change Password (authenticated)
# ---------------------------------------------------------------------------

@extend_schema(tags=["Account"])
class ChangePasswordView(APIView):
    """
    Change password for an authenticated user.

    Requires a valid JWT access token in the Authorization header.
    The current password must be supplied alongside the new password.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [PasswordResetThrottle]
    @extend_schema(
        operation_id="account_change_password",
        summary="Change password (requires authentication)",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Current password is incorrect"),
        },
        examples=[
            OpenApiExample(
                "Change Password Example",
                value={
                    "old_password": "OldStrongPassword123!",
                    "new_password": "NewStrongPassword123!"
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        service = _get_user_service()
        service.reset_password(
            email=request.user.email,
            old_password=serializer.validated_data["old_password"],
            new_password=serializer.validated_data["new_password"],
        )

        return success_response(
            data=None,
            message="Password changed successfully.",
        )


# ---------------------------------------------------------------------------
# Request Change Email — OTP step 1 (authenticated)
# ---------------------------------------------------------------------------

@extend_schema(tags=["Email Change"])
class RequestChangeEmailView(APIView):
    """
    Step 1 of the OTP-based email change flow.

    Verifies the user's current password, checks the new address is free,
    then sends a 6-digit OTP to the new email. The OTP is valid for 10 minutes.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [SendVerificationEmailThrottle]
    @extend_schema(
        operation_id="account_request_change_email",
        summary="Request email change — send OTP to new address",
        request=RequestChangeEmailSerializer,
        responses={
            200: OpenApiResponse(description="Verification code sent to the new email"),
            400: OpenApiResponse(description="Validation error or email delivery failure"),
            401: OpenApiResponse(description="Password is incorrect"),
            409: OpenApiResponse(description="New email already in use"),
        },
        examples=[
            OpenApiExample(
                "Request Change Email Example",
                value={
                    "new_email": "newuser@example.com",
                    "password": "StrongPassword123!"
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        service=_get_user_service()
        serializer = RequestChangeEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service.request_email_change(
                user=request.user,
                new_email=serializer.validated_data["new_email"],
                password=serializer.validated_data["password"],
            )
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )

        return success_response(
            data=None,
            message="Verification code sent to the new email.",
        )


# ---------------------------------------------------------------------------
# Verify Change Email — OTP step 2 (authenticated)
# ---------------------------------------------------------------------------

@extend_schema(tags=["Email Change"])
class VerifyChangeEmailView(APIView):
    """
    Step 2 of the OTP-based email change flow.

    Validates the 6-digit OTP from cache and, on success, updates the
    authenticated user's email address in the database.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="account_verify_change_email",
        summary="Verify OTP and apply the new email address",
        request=VerifyChangeEmailSerializer,
        responses={
            200: OpenApiResponse(description="Email updated successfully"),
            400: OpenApiResponse(description="Invalid or expired verification code"),
        },
        examples=[
            OpenApiExample(
                "Verify Change Email Example",
                value={
                    "new_email": "newuser@example.com",
                    "code": "123456"
                },
                request_only=True
            )
        ]
    )
    def post(self, request: Request):
        service = _get_user_service()
        serializer = VerifyChangeEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service.verify_email_change(
                user=request.user,
                new_email=serializer.validated_data["new_email"],
                code=serializer.validated_data["code"],
            )
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )

        return success_response(
            data=None,
            message="Email updated successfully.",
        )


# ---------------------------------------------------------------------------
# Admin — List Users
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin"])
class AdminUserListView(PaginationMixin, APIView):
    """
    GET /api/admin/users               — List all users.
    GET /api/admin/users?type=customer — Filter by account type.

    Supported types: customer, admin
    """
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_list_users",
        summary="List all users (optionally filtered by account type)",
        responses={200: UserProfileSerializer(many=True)},
        examples=[
            OpenApiExample(
                "List All Users Response",
                value={"status": True, "message": "Users retrieved successfully", "data": {"count": 2, "next": None, "previous": None, "results": [
                    {
                        "full_name": "John Doe",
                        "email": "customer@example.com",
                        "phone_number": "+201001234567",
                        "profile_image": None,
                        "notification_ids": ["fcm_token_xyz"],
                        "is_verified": True,
                        "is_banned": False,
                        "nationality": "Egyptian",
                        "address": "123 Main St, Cairo",
                        "account_type": "customer",
                        "specific_data": {"date_of_birth": "1990-01-15", "gender": "male"},
                    },
                    {
                        "full_name": "Admin User",
                        "email": "admin@example.com",
                        "phone_number": "+201001234567",
                        "profile_image": None,
                        "notification_ids": ["fcm_token_xyz"],
                        "is_verified": True,
                        "is_banned": False,
                        "nationality": "Egyptian",
                        "address": "123 Main St, Cairo",
                        "account_type": "admin",
                        "specific_data": None,
                    }

                ]}},
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request: Request):
        account_type = request.query_params.get("account_type")
        service = _get_user_service()
        try:
            users = service.list_users(account_type=account_type)
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )
        return self.paginate_and_respond(users, UserProfileSerializer, request, "Users retrieved successfully")


# ---------------------------------------------------------------------------
# Admin — Get User by ID
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin"])
class AdminUserDetailView(APIView):
    """GET /api/admin/users/<user_id> — Retrieve a single user by ID."""
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_get_user",
        summary="Get a user by ID",
        responses={
            200: UserProfileSerializer,
            404: OpenApiResponse(description="User not found"),
        },
        examples=[
            OpenApiExample(
                "Get User Response",
                value={
                    "full_name": "John Doe",
                    "email": "user@example.com",
                    "phone_number": "+201001234567",
                    "profile_image": "http://example.com/media/users/profile_images/photo.jpg",
                    "notification_ids": ["fcm_token_xyz"],
                    "is_verified": True,
                    "is_banned": False,
                    "nationality": "Egyptian",
                    "address": "123 Main St, Cairo",
                    "account_type": "customer",
                    "specific_data": {"date_of_birth": "1990-01-15", "gender": "male"},
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "User Not Found",
                value={"message": "User not found", "errors": {}},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def get(self, request: Request, user_id: int):
        service = _get_user_service()
        try:
            user = service.get_by_id(user_id)
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )
        return success_response(
            data=UserProfileSerializer(user, context={"request": request}).data,
            message="User retrieved successfully",
        )


# ---------------------------------------------------------------------------
# Ban / Unban User (admin only)
# ---------------------------------------------------------------------------

@extend_schema(tags=["Admin"])
class BanUserView(APIView):
    """
    POST   /api/admin/users/<user_id>/ban   — Ban a user account.
    DELETE /api/admin/users/<user_id>/ban   — Lift the ban.

    Admin-only. Banned users are blocked at login.
    """
    permission_classes = [IsAdminAccount]

    @extend_schema(
        operation_id="admin_ban_user",
        summary="Ban a user account",
        request=None,
        responses={
            200: OpenApiResponse(description="User banned successfully"),
            403: OpenApiResponse(description="Admin accounts cannot be banned"),
            404: OpenApiResponse(description="User not found"),
        },
        examples=[
            OpenApiExample(
                "Ban User Response",
                value={"message": "User banned successfully", "data": None},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "Ban Admin Account — Forbidden",
                value={"message": "Admin accounts cannot be banned", "errors": {}},
                response_only=True,
                status_codes=["403"],
            ),
            OpenApiExample(
                "User Not Found",
                value={"message": "User not found", "errors": {}},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def post(self, request: Request, user_id: int):
        service = _get_user_service()
        try:
            service.ban_user(user_id)
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )
        return success_response(data=None, message="User banned successfully")

    @extend_schema(
        operation_id="admin_unban_user",
        summary="Unban a user account",
        request=None,
        responses={
            200: OpenApiResponse(description="User unbanned successfully"),
            404: OpenApiResponse(description="User not found"),
        },
        examples=[
            OpenApiExample(
                "Unban User Response",
                value={"message": "User unbanned successfully", "data": None},
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                "User Not Found",
                value={"message": "User not found", "errors": {}},
                response_only=True,
                status_codes=["404"],
            ),
        ],
    )
    def delete(self, request: Request, user_id: int):
        service = _get_user_service()
        try:
            service.unban_user(user_id)
        except ApplicationError as exc:
            return error_response(
                message=exc.message,
                errors=exc.errors,
                status_code=exc.status_code,
            )
        return success_response(data=None, message="User unbanned successfully")


# ---------------------------------------------------------------------------
# Set FCM Token
# ---------------------------------------------------------------------------

@extend_schema(tags=["Profile"])
class SetFcmTokenView(APIView):
    """
    POST /api/set-fcm-token — Register or refresh an FCM device token.

    Called by the mobile app whenever Firebase rotates the push-notification
    token for the current device. Authenticated endpoint — JWT required.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="set_fcm_token",
        summary="Register or update the FCM push-notification token for this device",
        request=SetFcmTokenSerializer,
        responses={
            200: OpenApiResponse(description="FCM token saved successfully"),
            400: OpenApiResponse(description="Validation failed"),
        },
        examples=[
            OpenApiExample(
                "Set FCM Token Response",
                value={"status": True, "message": "FCM token saved successfully", "data": None},
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request: Request):
        serializer = SetFcmTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        service = _get_user_service()
        service.set_fcm_token(request.user, serializer.validated_data["fcm_token"])
        return success_response(data=None, message="FCM token saved successfully")
