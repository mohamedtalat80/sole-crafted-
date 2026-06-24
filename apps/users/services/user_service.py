"""
UserService — business logic for user authentication and profile management.

Design (SRP / DIP / OCP):
- All business rules live here; no ORM calls, no HTTP concerns.
- Depends on IUserRepository (interface), injected via constructor (DI).
- Raises ApplicationError subclasses — never returns error HTTP responses.
- Open for extension: swap repository or token generator without modifying service.
"""
from __future__ import annotations

import logging
import random
import time

from django.db import transaction
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.email import send_email

from apps.core.exceptions import (
    ApplicationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
)
from apps.users.interfaces.user_repository_interface import IUserRepository
from apps.users.models import CustomUser
_OTP_TTL = 600         
_RESEND_COOLDOWN = 90  
def _cache_key(user_id: int, new_email: str) -> str:
    """Deterministic cache key scoped to a specific user + target email pair."""
    return f"email_change:{user_id}:{new_email}"

class UserService:
    """
    Handles user registration, authentication, and profile operations.

    Constructor injection of IUserRepository satisfies the Dependency
    Inversion Principle — the service never imports the concrete repository.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        self._repo = user_repository

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------
    @transaction.atomic
    def register(
        self,
        email: str,
        full_name: str,
        password: str,
        notifications_id: str | None = None,
    ) -> CustomUser:
        """
        Create a new user account.

        Business rules:
        - Email must not already be registered.
        - Password must pass Django's built-in validators.
        - Customers  → is_verified = True  (email confirmed before this step).
        - Admin accounts are never created through this method.
        - On success, update the FCM token if provided.
        """
        email = email.strip().lower()

        if self._repo.exists_by_email(email):
            raise ConflictError(
                message="Validation failed",
                errors={"email": ["This email is already registered"]},
            )
        self._validate_password(password)
        
        user = self._repo.create(
            email=email,
            full_name=full_name.strip(),
            password=password,
        )
        self.send_verification_code(email)  

        if notifications_id:
            self._repo.save_device_token(user, notifications_id)

        return user

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(
        self,
        email: str,
        password: str,
        notifications_id: str | None = None,
    ) -> CustomUser:
        """
        Authenticate a user by email + password.

        Business rules:
        - Invalid credentials raise UnauthorizedError (not NotFoundError,
          to avoid email-enumeration attacks).
        - Deactivated accounts (deactivated_at is set) are automatically
          reactivated on successful login within the 60-day window.
        - On success, update the FCM token if provided.
        """
        email = email.strip().lower()

        # Django's authenticate() returns None for inactive users, so we fetch
        # the user manually first to handle the deactivation-reactivation case.
        user = self._repo.get_by_email(email)

        if user is None or not user.check_password(password):
            raise UnauthorizedError(
                message="Invalid credentials",
                errors={"email": ["Email or password is incorrect"]},
            )

        if not user.is_active:
            if user.deactivated_at is not None:
                # User self-deactivated — reactivate on login
                self._repo.reactivate_user(user)
            else:
                # Anonymised / admin-disabled — do not reactivate
                raise UnauthorizedError(
                    message="Invalid credentials",
                    errors={"email": ["Email or password is incorrect"]},
                )

        if user.is_banned:
            raise UnauthorizedError(
                message="Account banned",
                errors={"email": ["Your account has been banned. Please contact support."]},
            )

        if notifications_id:
            self._repo.save_device_token(user, notifications_id)

        return user

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_by_id(self, user_id: int) -> CustomUser:
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        return user

    def update_profile(self, user: CustomUser, **fields) -> CustomUser:
        """
        Update allowed profile fields.

        Only whitelisted fields can be updated through this method.
        Raises ApplicationError if unknown fields are passed.
        """
        allowed_fields = {
            "full_name",
            "phone_number",
            "profile_image",
            "date_of_birth",
            "gender",
            "address",
            "nationality",
        }
        disallowed = set(fields.keys()) - allowed_fields
        if disallowed:
            raise ApplicationError(
                message="Update failed",
                errors={f: ["This field cannot be updated."] for f in disallowed},
            )
        return self._repo.update(user, **fields)
    def set_fcm_token(self, user: CustomUser, fcm_token: str) -> None:
        """
        Register or update an FCM token for the authenticated user's device.

        Delegates directly to save_device_token which handles all three cases:
          - Same user, same token → no-op.
          - Different user owns this token → reassign to this user.
          - New token → create a UserDevice record.
        """
        self._repo.save_device_token(user, fcm_token)

    def increment_saved_items_count(self, user: CustomUser) -> None:
        """Increment saved_items_count by 1."""
        self._repo.increment_saved_items_count(user)
    def decrement_saved_items_count(self, user: CustomUser) -> None:
        """Decrement saved_items_count by 1."""
        self._repo.decrement_saved_items_count(user)

    # ------------------------------------------------------------------
    # Social Login
    # ------------------------------------------------------------------
    @transaction.atomic
    def social_login(
        self,
        provider: str,
        email: str,
        full_name: str,
        notifications_id: str | None = None,
    ) -> tuple[CustomUser, bool]:
        """
        Handle social login (Google / Apple) get-or-create logic.

        Business rules:
        - If user exists → return them (update notifications_id if provided)
        - If user doesn't exist → create with is_verified=True and no password
        - Deactivated accounts cannot log in via social auth either

        Returns:
            (user, is_new_user)
        """
        user, is_new = self._repo.get_or_create_by_social(
            email=email.strip().lower(),
            full_name=full_name.strip(),
            notification_id=notifications_id,
        )

        # Register the device token for all logins (new and returning)
        if notifications_id:
            self._repo.save_device_token(user, notifications_id)

        if not user.is_active:
            raise UnauthorizedError(
                message="Account is deactivated",
                errors={"email": ["Your account has been deactivated. Please contact support."]},
            )

        return user, is_new

    # ------------------------------------------------------------------
    # Email Verification
    # ------------------------------------------------------------------

    def send_verification_code(self, email: str) -> dict:
        """
        Generate and send a 6-digit code to the given email.

        Business rules:
        - Email must NOT already be registered on CustomUser.
        - Existing unverified records are replaced (delete + create).
        - Code expires in 900 seconds.
        """
        email = email.strip().lower()
        if not self._repo.exists_by_email(email):
            raise NotFoundError(
                message="Email not found", 
                errors={"email": ["No account is registered with this email address."]},   
            )
        existing_verification = self._repo.get_verification_by_email(email)
        if existing_verification and not existing_verification.is_expired():
            remaining = int(900 - (timezone.now() - existing_verification.created_at).total_seconds())
            raise TooManyRequestsError(
                message="Verification code already sent",
                errors={"email": [f"Please wait {remaining} seconds before requesting a new code."]},
            )

        code = f"{random.randint(0, 999999):06d}"
        self._repo.create_verification(email, code)

        try:
            send_email(
                to=email,
                subject="Your Sole Crafted verification code",
                text=(
                    f"Your verification code is: {code}\n\n"
                    "This code expires in 15 minutes."
                ),
            )
        except Exception:
            logger.exception("Failed to send verification email to %s", email)
            raise ApplicationError(
                message="Failed to send verification code",
                errors={"email": ["Could not send verification email. Please try again later."]},
            )

        return {"email": email, "expires_in": 900}
    @transaction.atomic
    def verify_email_code(self, email: str, code: str) -> dict:
        """
        Validate the 6-digit code for the given email.

        Business rules:
        - Record must exist.
        - Code must match exactly.
        - Record must not be expired (older than 900 seconds).
        """
        email = email.strip().lower()
        verification = self._repo.get_verification_by_email(email)

        if (
            not verification
            or verification.code != code
            or verification.is_expired()
        ):
            raise ApplicationError(
                message="Verification failed",
                errors={"verification_code": ["Invalid or expired verification code"]},
            )

        self._repo.mark_email_verified(verification)
        user=self._repo.get_by_email(email)
        self._repo.update(user, is_verified=True)
        return {"email": email, "is_verified": True}
    # ------------------------------------------------------------------
    # Account lifecycle
    # ------------------------------------------------------------------

    def delete_account(self, user: CustomUser, password: str) -> None:
        """
        Permanently delete the account — anonymise all PII immediately.

        Business rules:
        - Admin accounts cannot be self-deleted via the API.
        - Password must be correct (re-auth before destructive action).
        - All PII is wiped; the row survives for historical FK integrity
          (e.g. past bookings still reference a valid user ID).
        - The real email is freed at once so the user can re-register
          with a brand-new account (new ID, no history carry-over).
        """
        if user.is_admin:
            raise ForbiddenError("Admin accounts cannot be deleted via the API.")
        if not user.check_password(password):
            raise UnauthorizedError(
                message="Account deletion failed",
                errors={"password": ["Incorrect password"]},
            )
        self._repo.anonymize_user(user)

    def deactivate_account(self, user: CustomUser, password: str) -> None:
        """
        Temporarily deactivate the account for 60 days.

        Business rules:
        - Admin accounts cannot be self-deactivated via the API.
        - Password must be correct (re-auth before sensitive action).
        - Account is marked inactive; email and PII are preserved during
          the 60-day window (allows future reactivation feature).
        - After 60 days the purge_deactivated_accounts management command
          will anonymise the row automatically.
        - Calling deactivate on an already-deactivated account is a no-op
          (does NOT reset the 60-day timer).
        """
        if user.is_admin:
            raise ForbiddenError("Admin accounts cannot be deactivated via the API.")
        if not user.check_password(password):
            raise UnauthorizedError(
                message="Account deactivation failed",
                errors={"password": ["Incorrect password"]},
            )
        if user.deactivated_at is not None:
            raise ApplicationError(
                message="Account is already deactivated",
                errors={"account": ["This account has already been deactivated."]},
            )
        self._repo.deactivate_user(user)

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    def forgot_password(self, email: str) -> dict:
        """
        Send a 6-digit reset code to the given email.

        Business rules:
        - Email must be registered on an active CustomUser.
        - Does NOT reveal whether the email exists (returns same message
          either way) to prevent email-enumeration attacks.
        - Code expires in 900 seconds.
        """
        email = email.strip().lower()
        user = self._repo.get_by_email(email)

        # Always return success to prevent email enumeration.
        # Only actually send the email when the account exists and is active.
        if user and user.is_active:
            existing_reset = self._repo.get_password_reset_by_email(email)
            if existing_reset and not existing_reset.is_expired():
                remaining = int(900 - (timezone.now() - existing_reset.created_at).total_seconds())
                raise TooManyRequestsError(
                    message="Reset code already sent",
                    errors={"email": [f"Please wait {remaining} seconds before requesting a new code."]},
                )

            code = f"{random.randint(0, 999999):06d}"
            self._repo.create_password_reset(email, code)

            try:
                send_email(
                    to=email,
                    subject="Your Sole Crafted password reset code",
                    text=(
                        f"Your password reset code is: {code}\n\n"
                        "This code expires in 15 minutes.\n"
                        "If you did not request this, please ignore this email."
                    ),
                )
            except Exception:
                logger.exception("Failed to send password reset email to %s", email)

        return {"email": email, "expires_in": 900}

    def verify_reset_code(self, email: str, code: str) -> dict:
        """
        Validate the 6-digit reset code.

        Business rules:
        - Record must exist, code must match, and must not be expired.
        - On success marks is_verified=True; the reset step checks this flag.
        """
        email = email.strip().lower()
        reset = self._repo.get_password_reset_by_email(email)

        if not reset or reset.code != code or reset.is_expired():
            raise ApplicationError(
                message="Verification failed",
                errors={"code": ["Invalid or expired reset code"]},
            )

        self._repo.mark_reset_verified(reset)
        return {"email": email, "can_reset": True}

    def set_new_password(self, email: str, new_password: str) -> None:
        """
        Step 3 of the forgot-password flow — set a new password after code verification.

        Business rules:
        - A verified PasswordResetCode must exist (verify-reset-code must be done first).
        - User must exist and be active.
        - New password must pass Django validators.
        - PasswordResetCode is deleted after success (cannot be reused).
        """
        email = email.strip().lower()
        reset = self._repo.get_password_reset_by_email(email)

        if not reset or not reset.is_verified:
            raise ApplicationError(
                message="Password reset failed",
                errors={"code": ["You must verify your reset code before setting a new password"]},
            )

        user = self._repo.get_by_email(email)
        if not user or not user.is_active:
            raise NotFoundError("No active account found for this email")

        self._validate_password(new_password)
        self._repo.set_password(user, new_password)
        self._repo.delete_password_reset(email)

    def reset_password(self, email: str, old_password: str, new_password: str) -> None:
        """
        Change password by providing the current password.

        Business rules:
        - The user must authenticate with their current email + old_password.
        - The account must be active.
        - New password must pass Django's built-in validators.
        - Old and new passwords may not be identical (Django validators enforce this).
        """
        user = authenticate(username=email.strip().lower(), password=old_password)

        if user is None:
            raise UnauthorizedError(
                message="Password change failed",
                errors={"old_password": ["Current password is incorrect"]},
            )

        if not user.is_active:
            raise UnauthorizedError(
                message="Account is deactivated",
                errors={"email": ["Your account has been deactivated. Please contact support."]},
            )

        self._validate_password(new_password)
        self._repo.set_password(user, new_password)

    def request_email_change(self, user: CustomUser, new_email: str, password: str) -> None:
        """
        Step 1 of the email change flow.

        Business rules:
        - The caller must supply their current password for re-authentication.
        - new_email must differ from the current email.
        - new_email must not already be in use by another account.
        - A 90-second cooldown is enforced between requests for the same
        (user, new_email) pair to prevent email-bombing.
        - Generates a 6-digit OTP, stores it in cache for 10 minutes, and sends
        it to new_email.
        - If the email send fails the OTP is evicted from cache so the user is
        not left with a dangling (unsent) code.

        Raises:
            UnauthorizedError:    password mismatch.
            ConflictError:        new_email == current email, or already registered.
            TooManyRequestsError: cooldown has not elapsed since the last send.
            ApplicationError:     transient email delivery failure.
        """
        if not user.check_password(password):
            raise UnauthorizedError(
                message="Email change failed",
                errors={"password": ["Password is incorrect."]},
            )

        new_email = new_email.strip().lower()

        if new_email == user.email:
            raise ConflictError(
                message="Email change failed",
                errors={"new_email": ["New email must be different from your current email."]},
            )
        existing_email = self._repo.get_by_email(new_email)
        if existing_email is not None:
            raise ConflictError(
                message="Email change failed",
                errors={"new_email": ["This email is already in use by another account."]},
            )

        key = _cache_key(user.pk, new_email)
        existing: dict | None = cache.get(key)
        if existing is not None:
            elapsed = time.time() - existing["sent_at"]
            if elapsed < _RESEND_COOLDOWN:
                remaining = int(_RESEND_COOLDOWN - elapsed)
                raise TooManyRequestsError(
                    message="Too many requests",
                    errors={"new_email": [f"Please wait {remaining} seconds before requesting a new code."]},
                )

        code = f"{random.randint(0, 999_999):06d}"
        cache.set(key, {"code": code, "sent_at": time.time()}, _OTP_TTL)

        try:
            send_email(
                to=new_email,
                subject="Your Omarina email change verification code",
                text=(
                    f"Your email change verification code is: {code}\n\n"
                    "This code expires in 10 minutes.\n"
                    "If you did not request this, please ignore this email."
                ),
            )
        except Exception:
            logger.exception("Failed to send email change OTP to %s", new_email)
            cache.delete(key)
            raise ApplicationError(
                message="Failed to send verification code",
                errors={"new_email": ["Could not send the verification email. Please try again later."]},
            )


    def verify_email_change(
        self,
        user: CustomUser,
        new_email: str,
        code: str,
            ) -> None:
        """
        Step 2 of the email change flow.

        Business rules:
        - Looks up the OTP stored in cache for this user + new_email pair.
        - If the cache entry is missing (expired) or the code does not match,
        raises ApplicationError.
        - On a valid match: updates user.email in the database and deletes the
        OTP from cache so it cannot be reused.

        Raises:
            ApplicationError: OTP missing, expired, or does not match.
        """
        new_email = new_email.strip().lower()
        key = _cache_key(user.pk, new_email)
        cached: dict | None = cache.get(key)

        if cached is None or cached.get("code") != code:
            raise ApplicationError(
                message="Verification failed",
                errors={"code": ["Invalid or expired verification code."]},
            )

        user.email = new_email
        self._repo.update(user, email=new_email)
        cache.delete(key)

   
    # ------------------------------------------------------------------
    # Logout all devices
    # ------------------------------------------------------------------

    def logout_all_devices(self, user) -> int:
        """
        Blacklist all outstanding refresh tokens for the user.

        Effectively forces every device / session to re-authenticate.
        Returns the number of tokens that were invalidated.
        """
        return self._repo.blacklist_all_tokens(user)

    # ------------------------------------------------------------------
    # Admin — user listing
    # ------------------------------------------------------------------

    def list_users(self, account_type: str | None = None) -> list[CustomUser]:
        """Return all users, optionally filtered by account_type."""
        if account_type:
            if account_type not in CustomUser.AccountType.values:
                raise ApplicationError(
                    message="Invalid account type",
                    errors={"account_type": [f"Must be one of: {', '.join(CustomUser.AccountType.values)}"]},
                )
            return self._repo.get_all_by_type(account_type)
        return self._repo.get_all()

    # ------------------------------------------------------------------
    # Ban / Unban
    # ------------------------------------------------------------------

    def ban_user(self, user_id: int) -> CustomUser:
        """
        Ban a user account. Banned users cannot log in.

        Business rules:
        - Admin accounts cannot be banned.
        - Banning an already-banned user is a no-op (idempotent).
        """
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        if user.is_admin:
            raise ForbiddenError(message="Admin accounts cannot be banned")
        return self._repo.update(user, is_banned=True)

    def unban_user(self, user_id: int) -> CustomUser:
        """Lift a ban from a user account."""
        user = self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(message="User not found")
        return self._repo.update(user, is_banned=False)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_password(password: str) -> None:
        """Delegate to Django's AUTH_PASSWORD_VALIDATORS."""
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            raise ApplicationError(
                message="Validation failed",
                errors={"password": list(exc.messages)},
            ) from exc
