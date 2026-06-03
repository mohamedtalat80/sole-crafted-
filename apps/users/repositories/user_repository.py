"""
ORM-backed implementation of IUserRepository.

Design (SRP / DIP):
- This class is the ONLY place where Django ORM queries for users live.
- Services depend on IUserRepository (the interface), not this class directly.
- Injected via dependency injection in views/service constructors.
"""
from __future__ import annotations

from typing import Optional

import uuid
from datetime import timedelta

from django.db import IntegrityError
from django.db.models import F
from django.utils import timezone

from apps.users.interfaces.user_repository_interface import IUserRepository
from apps.users.models import CustomUser, CustomerProfile, EmailVerification, PasswordResetCode, UserDevice


class UserRepository(IUserRepository):
    """Concrete repository backed by Django ORM."""

    def get_by_id(self, user_id: int) -> Optional[CustomUser]:
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None

    def get_by_email(self, email: str) -> Optional[CustomUser]:
        try:
            return CustomUser.objects.get(email=email.lower())
        except CustomUser.DoesNotExist:
            return None

    def exists_by_email(self, email: str) -> bool:
        return CustomUser.objects.filter(email=email.lower()).exists()

    def create(
        self,
        email: str,
        full_name: str,
        password: str,
        is_verified: bool = False,
    ) -> CustomUser:
        return CustomUser.objects.create_user(
            email=email,
            full_name=full_name,
            password=password,
            is_verified=is_verified,
            account_type=CustomUser.AccountType.CUSTOMER,  # Default to customer for regular signups
        )

    def update(self, user: CustomUser, **fields) -> CustomUser:
        for attr, value in fields.items():
            setattr(user, attr, value)
        user.save(update_fields=list(fields.keys()) + ["updated_at"])
        return user

    def save_device_token(
        self,
        user: CustomUser,
        token: str,
        device_type: str | None = None,
    ) -> UserDevice:
        """
        Register an FCM token for the user's device.

        - Same user, same token → no-op (return existing record).
        - Different user owns this token → reassign to the current user.
          (Happens when someone sells their phone and the new owner logs in.)
        - Token not seen before → create a new UserDevice record.
        """
        try:
            device = UserDevice.objects.get(fcm_token=token)
            if device.user_id != user.pk:
                device.user = user
                device.save(update_fields=["user"])
            return device
        except UserDevice.DoesNotExist:
            return UserDevice.objects.create(
                user=user,
                fcm_token=token,
                device_type=device_type,
            )
    def increment_saved_items_count(self, user: CustomUser) -> None:
        """Increment saved_items_count by 1."""
        CustomerProfile.objects.filter(user=user).update(saved_items_count=F("saved_items_count") + 1)
    def decrement_saved_items_count(self, user: CustomUser) -> None:
        """Decrement saved_items_count by 1, floor at 0."""
        CustomerProfile.objects.filter(user=user, saved_items_count__gt=0).update(
            saved_items_count=F("saved_items_count") - 1
        )
    def get_or_create_by_social(
        self,
        email: str,
        full_name: str,
    ) -> tuple[CustomUser, bool]:
        """
        Look up a user by email. If found, return them.
        If not found, create a new social-auth user with:
          - is_verified=True (social accounts are pre-verified)
          - unusable password (no email/password login)

        Race-condition safe: if two concurrent requests try to create
        the same user, the second one catches the IntegrityError from
        the UNIQUE email constraint and falls back to a GET.
        """
        email = email.lower()
        try:
            user = CustomUser.objects.get(email=email)
            return user, False
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser(
                    email=email,
                    full_name=full_name,
                    account_type=CustomUser.AccountType.CUSTOMER,
                    is_verified=True,
                )
                user.set_unusable_password()
                user.save()
                return user, True
            except IntegrityError:
                user = CustomUser.objects.get(email=email)
                return user, False

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    def create_verification(self, email: str, code: str) -> EmailVerification:
        """
        Delete any existing record for this email and create a fresh one.
        Re-creating resets created_at so the 900-second expiry is correct.
        """
        EmailVerification.objects.filter(email=email).delete()
        return EmailVerification.objects.create(email=email, code=code)

    def get_verification_by_email(self, email: str) -> EmailVerification | None:
        try:
            return EmailVerification.objects.get(email=email)
        except EmailVerification.DoesNotExist:
            return None

    def mark_email_verified(self, verification: EmailVerification) -> None:
        verification.is_verified = True
        verification.save(update_fields=["is_verified"])

    def delete_verification(self, email: str) -> None:
        EmailVerification.objects.filter(email=email).delete()

    # ------------------------------------------------------------------
    # Account lifecycle
    # ------------------------------------------------------------------

    def anonymize_user(self, user: CustomUser) -> None:
        """
        Irreversibly wipe PII from the user row.

        Email becomes `deleted_<uuid>@omarina.invalid` — a non-deliverable
        address that frees the real email for future re-registration while
        keeping the row (and its FK relations) intact for historical records.
        """
        placeholder_email = f"deleted_{uuid.uuid4().hex}@omarina.invalid"
        user.email = placeholder_email
        user.full_name = "Deleted User"
        user.phone_number = None
        user.profile_image = None
        user.date_of_birth = None
        user.gender = None
        user.address = None
        user.is_active = False
        user.deactivated_at = None
        user.set_unusable_password()
        # Remove all FCM device tokens so push notifications stop immediately.
        user.devices.all().delete()
        user.save(update_fields=[
            "email", "full_name", "phone_number", "profile_image",
            "date_of_birth", "gender", "address",
            "is_active", "deactivated_at", "password", "updated_at",
        ])

    def deactivate_user(self, user: CustomUser) -> None:
        """Set is_active=False and stamp deactivated_at with the current time."""
        user.is_active = False
        user.deactivated_at = timezone.now()
        user.save(update_fields=["is_active", "deactivated_at", "updated_at"])

    def reactivate_user(self, user: CustomUser) -> None:
        """Restore a self-deactivated account to active status."""
        user.is_active = True
        user.deactivated_at = None
        user.save(update_fields=["is_active", "deactivated_at", "updated_at"])

    def get_users_due_for_purge(self) -> list[CustomUser]:
        """Return users whose 60-day deactivation window has expired."""
        cutoff = timezone.now() - timedelta(days=60)
        return list(
            CustomUser.objects.filter(
                deactivated_at__isnull=False,
                deactivated_at__lte=cutoff,
            )
        )

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    def create_password_reset(self, email: str, code: str) -> PasswordResetCode:
        """Delete any existing record and insert a fresh one (resets created_at)."""
        PasswordResetCode.objects.filter(email=email).delete()
        return PasswordResetCode.objects.create(email=email, code=code)

    def get_password_reset_by_email(self, email: str) -> PasswordResetCode | None:
        try:
            return PasswordResetCode.objects.get(email=email)
        except PasswordResetCode.DoesNotExist:
            return None

    def mark_reset_verified(self, reset: PasswordResetCode) -> None:
        reset.is_verified = True
        reset.save(update_fields=["is_verified"])

    def delete_password_reset(self, email: str) -> None:
        PasswordResetCode.objects.filter(email=email).delete()

    def set_password(self, user: CustomUser, new_password: str) -> None:
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

    def get_all(self) -> list[CustomUser]:
        return list(CustomUser.objects.order_by("-created_at"))

    def get_all_by_type(self, account_type: str) -> list[CustomUser]:
        return list(CustomUser.objects.filter(account_type=account_type).order_by("-created_at"))

    def blacklist_all_tokens(self, user: CustomUser) -> int:
        """
        Invalidate every active session for this user.

        Two-pronged approach:
        1. Blacklist all outstanding refresh tokens so they cannot be used
           to obtain new access tokens.
        2. Stamp `tokens_invalidated_at = now()` on the user row so the
           custom JWT authenticator rejects any access token that was
           issued before this moment — even within its normal lifetime.

        Returns the count of refresh tokens that were newly blacklisted.
        """
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        outstanding = OutstandingToken.objects.filter(user=user)
        count = 0
        for token in outstanding:
            _, created = BlacklistedToken.objects.get_or_create(token=token)
            if created:
                count += 1

        # Stamp the invalidation time so the custom authenticator can
        # reject still-valid access tokens issued before this moment.
        user.tokens_invalidated_at = timezone.now()
        user.save(update_fields=["tokens_invalidated_at", "updated_at"])

        return count
