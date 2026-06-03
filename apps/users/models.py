"""
CustomUser model.

Fields sourced from the API docs and user stories:
  - account_type  : "customer" | "owner" | "captain" | "admin"
  - is_verified   : bool (customers start true; owners start false until admin approves)
  - profile_image : optional image
  - date_of_birth : optional date
  - gender        : "male" | "female" | null

Additional fields required for the auth flows documented in the API:
  - full_name
  - phone_number
  - address
  - notifications_id (FCM push token)
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class CustomUserManager(BaseUserManager):
    """Manager that uses email as the unique identifier instead of username."""

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError(_("The email address must be set."))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("account_type", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self._create_user(email, password, **extra_fields)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Platform user with one of four account types:
      - customer : end-user who books trips / rentals
      - owner    : service provider who lists boats and trips
      - captain  : boat captain (future feature — assigned to rentals by owners)
      - admin    : internal platform administrator (created via Django admin only)

    Design note (SRP): this model only holds identity and authentication data.
    Owner-specific profile data (company info, documents, payout methods) will
    live in separate models in their own apps to keep concerns separated.
    """

    class AccountType(models.TextChoices):
        CUSTOMER = "customer", _("Customer")
        ADMIN = "admin", _("Admin")

    class Gender(models.TextChoices):
        MALE = "male", _("Male")
        FEMALE = "female", _("Female")
        OTHER = "other", _("Other")

    # ------------------------------------------------------------------
    # Core identity fields
    # ------------------------------------------------------------------

    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
    )
    full_name = models.CharField(
        _("full name"),
        max_length=255,
    )
    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        blank=True,
        null=True,
        unique=True,
    )

    # ------------------------------------------------------------------
    # Account classification (from docs)
    # ------------------------------------------------------------------

    account_type = models.CharField(
        _("account type"),
        max_length=10,
        choices=AccountType.choices,
        default=AccountType.CUSTOMER,
        db_index=True,
    )
    is_verified = models.BooleanField(
        _("verified"),
        default=False,
        help_text=_(
            "Customers are verified immediately after email confirmation. "
            "Owners become verified after admin approves their documents."
        ),
    )

    # ------------------------------------------------------------------
    # Profile fields (from docs)
    # ------------------------------------------------------------------

    profile_image = models.ImageField(
        _("profile image"),
        upload_to="users/profile_images/%Y/%m/",
        blank=True,
        null=True,
    )
    date_of_birth = models.DateField(
        _("date of birth"),
        blank=True,
        null=True,
    )
    gender = models.CharField(
        _("gender"),
        max_length=10,
        choices=Gender.choices,
        blank=True,
        null=True,
    )
    address = models.TextField(
        _("address"),
        blank=True,
        null=True,
    )
    nationality = models.CharField(
        _("nationality"),
        max_length=100,
        blank=True,
        null=True,
    )

    # ------------------------------------------------------------------
    # Auth / admin flags
    # ------------------------------------------------------------------

    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    is_banned = models.BooleanField(
        _("banned"),
        default=False,
        help_text=_("Banned users cannot log in or access the platform."),
    )

    # ------------------------------------------------------------------
    # Account lifecycle
    # ------------------------------------------------------------------

    # Set when the user requests a 60-day deactivation.
    # Null = account is active (or permanently deleted/anonymized).
    # The purge_deactivated_accounts management command anonymizes rows
    # where deactivated_at + 60 days <= now().
    deactivated_at = models.DateTimeField(
        _("deactivated at"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_(
            "Timestamp when the 60-day deactivation was requested. "
            "Account will be permanently purged after 60 days."
        ),
    )

    # Set by logout-all-devices. Any access token issued BEFORE this
    # timestamp is rejected by the custom JWT authenticator, even if the
    # token has not yet expired.
    tokens_invalidated_at = models.DateTimeField(
        _("tokens invalidated at"),
        null=True,
        blank=True,
        help_text=_(
            "Access tokens issued before this timestamp are rejected. "
            "Updated whenever the user triggers logout-from-all-devices."
        ),
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    # ------------------------------------------------------------------
    # Manager & auth config
    # ------------------------------------------------------------------

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.full_name

    def get_full_name(self) -> str:
        """Used by Django admin and Jazzmin navbar display."""
        return self.full_name

    def get_short_name(self) -> str:
        """Returns first name portion for compact displays."""
        return self.full_name.split()[0] if self.full_name else self.email

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def is_customer(self) -> bool:
        return self.account_type == self.AccountType.CUSTOMER

    @property
    def is_admin(self) -> bool:
        return self.account_type == self.AccountType.ADMIN


# ---------------------------------------------------------------------------
# Customer Profile
# ---------------------------------------------------------------------------

class CustomerProfile(models.Model):
    """
    Extended profile for customer accounts.

    Stores customer-specific data (referral code, quiz preferences).
    Auto-created via post_save signal when a customer user is created.

    Why a separate model?
      CustomUser holds identity/auth data shared by all account types.
      Customer-specific fields live here so we don't bloat the user table
      with columns that only apply to one role.
    """

    # ── Link to the user ─────────────────────────────────────────────
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="customer_profile",
        verbose_name=_("user"),
    )

    # ── Customer-specific fields ─────────────────────────────────────
    # Auto-generated 8-char uppercase code (e.g. "A3F1B2C9").
    # Used for the referral / invite-a-friend feature.
    referral_code = models.CharField(
        _("referral code"),
        max_length=20,
        unique=True,
        blank=True,  # blank on forms — auto-filled in save()
    )

    # Tracks how many items (boats, trips, etc.) the customer has saved/favourited.
    # Incremented/decremented via F() expressions in the repository to avoid race conditions.
    saved_items_count = models.PositiveIntegerField(
        _("saved items count"),
        default=0,
    )

    # Stores the user's onboarding quiz answers as a JSON object.
    # Nullable because the quiz is optional / completed later.
    quiz_preferences = models.JSONField(
        _("quiz preferences"),
        null=True,
        blank=True,
        default=None,
        help_text=_("Stores onboarding quiz answers as JSON."),
    )

    # ── Timestamps ───────────────────────────────────────────────────
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("customer profile")
        verbose_name_plural = _("customer profiles")

    def __str__(self) -> str:
        return f"CustomerProfile({self.user.email})"

    def save(self, *args, **kwargs):
        # Auto-generate a unique referral code on first save.
        # Race-condition safe: if two concurrent saves generate the same
        # code, the DB UNIQUE constraint will reject the second one and
        # we retry with a new code.
        if not self.referral_code:
            self._save_with_unique_referral_code(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def _save_with_unique_referral_code(self, *args, **kwargs):
        """Try generating a unique code, retrying on DB collision."""
        from django.db import IntegrityError

        for _ in range(10):
            self.referral_code = uuid.uuid4().hex[:8].upper()
            try:
                super().save(*args, **kwargs)
                return
            except IntegrityError:
                # Code already taken — generate a new one and retry
                continue
        raise ValueError("Could not generate a unique referral code after 10 attempts.")



# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

class EmailVerification(models.Model):
    """
    Stores one-time 6-digit codes for pre-signup email verification.

    One record per email address - re-sending a code deletes the old record
    and inserts a fresh one so `created_at` resets and expiry is correct.

    A code is considered expired when `created_at` is older than 900 seconds.
    """

    email = models.EmailField(
        _("email"),
        unique=True,
        db_index=True,
    )
    code = models.CharField(
        _("verification code"),
        max_length=6,
    )
    is_verified = models.BooleanField(
        _("verified"),
        default=False,
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("email verification")
        verbose_name_plural = _("email verifications")

    def __str__(self) -> str:
        return f"EmailVerification({self.email})"

    def is_expired(self) -> bool:
        """Return True if the code was created more than 900 seconds ago."""
        from django.utils import timezone
        return (timezone.now() - self.created_at).total_seconds() > 900


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

class PasswordResetCode(models.Model):
    """
    Stores one-time 6-digit codes for password reset.

    Flow:
      1. User requests reset  -> record created (or replaced)
      2. User submits code    -> is_verified set to True
      3. User submits new password -> password updated, record deleted

    One record per email. Re-requesting replaces the old record so
    created_at resets and the 900-second expiry window is correct.
    """

    email = models.EmailField(
        _("email"),
        unique=True,
        db_index=True,
    )
    code = models.CharField(
        _("reset code"),
        max_length=6,
    )
    is_verified = models.BooleanField(
        _("code verified"),
        default=False,
        help_text=_("True once the user has confirmed the code; allows the reset step."),
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("password reset code")
        verbose_name_plural = _("password reset codes")

    def __str__(self) -> str:
        return f"PasswordResetCode({self.email})"

    def is_expired(self) -> bool:
        """Return True if the code is older than 900 seconds."""
        from django.utils import timezone
        return (timezone.now() - self.created_at).total_seconds() > 900


# ---------------------------------------------------------------------------
# User Devices (FCM tokens — one per physical device)
# ---------------------------------------------------------------------------

class UserDevice(models.Model):
    """
    Maps an FCM push-notification token to a specific user device.

    Why a separate table (not a single column on CustomUser)?
      A user can be logged in on multiple devices simultaneously (phone +
      tablet). Storing one token per user would silently drop tokens on
      each new login. This model lets us fan-out a push notification to
      ALL of a user's active devices.

    Uniqueness rule:
      A token belongs to exactly one user at a time. If a device is
      handed to a new person who logs in with a different account, the
      token is re-assigned to that account (not duplicated).
    """

    class DeviceType(models.TextChoices):
        IOS = "ios", _("iOS")
        ANDROID = "android", _("Android")

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="devices",
        verbose_name=_("user"),
    )
    # FCM tokens are ~150-200 chars; TextField avoids length concerns.
    fcm_token = models.TextField(
        _("FCM token"),
        unique=True,
    )
    device_type = models.CharField(
        _("device type"),
        max_length=10,
        choices=DeviceType.choices,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("user device")
        verbose_name_plural = _("user devices")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"UserDevice({self.user.email} / {self.device_type or 'unknown'})"
