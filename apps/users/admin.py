from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from apps.users.models import CustomUser, CustomerProfile, EmailVerification, PasswordResetCode, UserDevice


# ---------------------------------------------------------------------------
# Profile inlines — shown inside the CustomUser admin page
# ---------------------------------------------------------------------------

class CustomerProfileInline(admin.StackedInline):
    """Inline display of CustomerProfile on the user admin page."""
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = _("Customer Profile")
    readonly_fields = ["referral_code", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Custom User Admin
# ---------------------------------------------------------------------------

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    ordering = ["-created_at"]
    list_display = ["email", "full_name", "account_type", "is_verified", "is_active", "created_at"]
    list_filter = ["account_type", "is_verified", "is_active", "gender"]
    search_fields = ["email", "full_name", "phone_number"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name", "phone_number", "profile_image", "date_of_birth", "gender", "address")}),
        (_("Account"), {"fields": ("account_type", "is_verified")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Timestamps"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "account_type", "password1", "password2"),
        }),
    )
    readonly_fields = ["created_at", "updated_at", "last_login"]

    def get_inlines(self, request, obj=None):
        """
        Dynamically show the correct profile inline based on account_type.
        This avoids showing an empty OwnerProfile form for customers, etc.
        """
        if obj is None:
            return []
        if obj.account_type == CustomUser.AccountType.CUSTOMER:
            return [CustomerProfileInline]
       
        return []


# ---------------------------------------------------------------------------
# Standalone Profile Admin pages
# ---------------------------------------------------------------------------

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "referral_code", "created_at"]
    search_fields = ["user__email", "user__full_name", "referral_code"]
    readonly_fields = ["referral_code", "created_at", "updated_at"]




@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ["email", "is_verified", "created_at"]
    list_filter = ["is_verified"]
    search_fields = ["email"]
    readonly_fields = ["code", "created_at"]


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ["email", "is_verified", "created_at"]
    list_filter = ["is_verified"]
    search_fields = ["email"]
    readonly_fields = ["code", "created_at"]


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ["user", "device_type", "created_at", "user_last_login"]
    list_filter = ["device_type"]
    search_fields = ["user__email", "user__full_name", "fcm_token"]
    readonly_fields = ["fcm_token", "created_at"]

    @admin.display(description="Last login", ordering="user__last_login")
    def user_last_login(self, obj):
        return obj.user.last_login
