from django.urls import path

from apps.users.views import (
    AccountView,
    AdminUserDetailView,
    AdminUserListView,
    BanUserView,
    ChangePasswordView,
    ForgotPasswordView,
    LogoutAllDevicesView,
    RequestChangeEmailView,
    SendVerificationCodeView,
    SetFcmTokenView,
    SetNewPasswordView,
    VerifyChangeEmailView,
    VerifyResetCodeView,
    LoginView,
    LogoutView,
    ProfileView,
    RefreshTokenView,
    SignUpView,
    SocialLoginView,
    VerifyEmailCodeView,
)

admin_urlpatterns = [
    path("users", AdminUserListView.as_view(), name="admin-list-users"),
    path("users/<int:user_id>", AdminUserDetailView.as_view(), name="admin-get-user"),
    path("users/<int:user_id>/ban", BanUserView.as_view(), name="admin-ban-user"),
]

urlpatterns = [
    path("signup", SignUpView.as_view(), name="auth-signup"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("logout-all-devices", LogoutAllDevicesView.as_view(), name="auth-logout-all-devices"),
    path("refresh", RefreshTokenView.as_view(), name="auth-refresh"),
    path("social-login", SocialLoginView.as_view(), name="auth-social-login"),
    path("profile", ProfileView.as_view(), name="auth-profile"),
    path("send-verification-code", SendVerificationCodeView.as_view(), name="auth-send-verification-code"),
    path("verify-email-code", VerifyEmailCodeView.as_view(), name="auth-verify-email-code"),
    path("account", AccountView.as_view(), name="auth-account"),
    path("forgot-password", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("verify-reset-code", VerifyResetCodeView.as_view(), name="auth-verify-reset-code"),
    path("set-new-password", SetNewPasswordView.as_view(), name="auth-set-new-password"),
    path("change-password", ChangePasswordView.as_view(), name="auth-change-password"),
    path("request-change-email", RequestChangeEmailView.as_view(), name="auth-request-change-email"),
    path("verify-change-email", VerifyChangeEmailView.as_view(), name="auth-verify-change-email"),
    path("set-fcm-token", SetFcmTokenView.as_view(), name="auth-set-fcm-token"),
]
