from django.urls import path
from .views import (
    RegisterView, EmailVerifyView, LoginView, RefreshTokenView, 
    LogoutView, ForgotPasswordView, VerifyOTPView, ResetPasswordView,VerifyingEmailForUnVerified
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', EmailVerifyView.as_view(), name='verify-email'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('reverify-email',VerifyingEmailForUnVerified.as_view(),name='reverify-email'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
] 