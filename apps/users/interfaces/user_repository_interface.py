"""
IUserRepository — abstract contract for user data access.

Design (DIP / ISP):
- Services depend on this interface, never on the concrete ORM repository.
- This makes it easy to swap implementations (e.g. ORM → cache → external API)
  without touching service code.
- Each method has one clear responsibility (ISP).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from apps.users.models import CustomUser, EmailVerification, PasswordResetCode, UserDevice


class IUserRepository(ABC):
    """Abstract repository for CustomUser persistence operations."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[CustomUser]:
        """Return the user with the given PK, or None."""

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[CustomUser]:
        """Return the user with the given email address, or None."""

    @abstractmethod
    def exists_by_email(self, email: str) -> bool:
        """Return True if a user with this email already exists."""

    @abstractmethod
    def create(
        self,
        email: str,
        full_name: str,
        password: str,
        is_verified: bool = False,
    ) -> CustomUser:
        """Create and persist a new user. Returns the saved instance."""

    @abstractmethod
    def update(self, user: CustomUser, **fields) -> CustomUser:
        """
        Update arbitrary fields on an existing user instance and save.
        Returns the updated instance.
        """

    @abstractmethod
    def save_device_token(
        self,
        user: CustomUser,
        token: str,
        device_type: str | None = None,
    ) -> UserDevice:
        """
        Register an FCM device token for the user.

        - Token already belongs to this user → no-op, return existing record.
        - Token belongs to another user → reassign it to this user.
        - Token is new → create a UserDevice record.
        """

    @abstractmethod
    def increment_saved_items_count(self, user: CustomUser) -> None:
        """Increment saved_items_count by 1."""
        pass
    @abstractmethod
    def decrement_saved_items_count(self, user: CustomUser) -> None:
        """Decrement saved_items_count by 1."""
        pass
    @abstractmethod
    def get_or_create_by_social(
        self,
        email: str,
        full_name: str,
    ) -> tuple[CustomUser, bool]:
        """
        Get an existing user by email, or create a new one for social login.

        Returns:
            (user, is_new_user) — is_new_user is True if the user was just created.

        New social users are created with:
            - is_verified = True (social accounts are pre-verified)
            - unusable password (they didn't sign up with email/password)
        """

    # ------------------------------------------------------------------
    # Email verification
    # ------------------------------------------------------------------

    @abstractmethod
    def create_verification(self, email: str, code: str) -> EmailVerification:
        """
        Delete any existing record for this email, then insert a fresh one.
        Re-creating (rather than updating) resets created_at for correct expiry.
        """

    @abstractmethod
    def get_verification_by_email(self, email: str) -> Optional[EmailVerification]:
        """Return the EmailVerification record for this email, or None."""

    @abstractmethod
    def mark_email_verified(self, verification: EmailVerification) -> None:
        """Set is_verified=True and persist."""

    @abstractmethod
    def delete_verification(self, email: str) -> None:
        """Delete the EmailVerification record for this email (post-signup cleanup)."""

    # ------------------------------------------------------------------
    # Account lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def anonymize_user(self, user: CustomUser) -> None:
        """
        Irreversibly wipe all PII from the user record.

        Sets email to a non-reusable placeholder (frees the real address),
        clears every personal field, marks is_active=False, and sets an
        unusable password. The row (and its FK relations) is kept so that
        historical records (bookings, etc.) remain consistent.
        """

    @abstractmethod
    def deactivate_user(self, user: CustomUser) -> None:
        """
        Temporarily deactivate the account.

        Sets is_active=False and stamps deactivated_at=now().
        The purge management command will anonymize this user after 60 days.
        """

    @abstractmethod
    def reactivate_user(self, user: CustomUser) -> None:
        """
        Restore a self-deactivated account to active status.

        Sets is_active=True and clears deactivated_at.
        Called automatically when the user logs in during the 60-day window.
        """

    @abstractmethod
    def get_users_due_for_purge(self) -> list[CustomUser]:
        """
        Return all users whose 60-day deactivation window has expired.

        Matches rows where deactivated_at is not null and
        deactivated_at + 60 days <= now().
        """

    # ------------------------------------------------------------------
    # Password reset
    # ------------------------------------------------------------------

    @abstractmethod
    def create_password_reset(self, email: str, code: str) -> PasswordResetCode:
        """Delete any existing record for this email and create a fresh one."""

    @abstractmethod
    def get_password_reset_by_email(self, email: str) -> Optional[PasswordResetCode]:
        """Return the PasswordResetCode record for this email, or None."""

    @abstractmethod
    def mark_reset_verified(self, reset: PasswordResetCode) -> None:
        """Set is_verified=True and persist."""

    @abstractmethod
    def delete_password_reset(self, email: str) -> None:
        """Delete the PasswordResetCode record after a successful reset."""

    @abstractmethod
    def set_password(self, user: CustomUser, new_password: str) -> None:
        """Hash and persist a new password for the given user."""

    @abstractmethod
    def get_all(self) -> list[CustomUser]:
        """Return all users ordered by creation date descending."""

    @abstractmethod
    def get_all_by_type(self, account_type: str) -> list[CustomUser]:
        """Return all users with the given account_type."""

    @abstractmethod
    def blacklist_all_tokens(self, user: CustomUser) -> int:
        """
        Blacklist every outstanding refresh token that belongs to this user.

        Returns the number of tokens blacklisted (useful for logging / tests).
        Already-blacklisted tokens are skipped.
        """
