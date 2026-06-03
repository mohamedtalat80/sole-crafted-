from django.urls import path
from apps.privacy_policy.views import (
    AdminPrivacyPolicyListCreateView,
    AdminPrivacyPolicyView,
    AdminPrivacyPolicyToggleActiveView,
    PrivacyPolicyView,
)

public_privacy_policy_urlpatterns = [
    path("", PrivacyPolicyView.as_view(), name="privacy-policy-list"),
]

admin_privacy_policy_urlpatterns = [
    path("privacy-policy/", AdminPrivacyPolicyListCreateView.as_view(), name="admin-privacy-policy-list"),
    path("privacy-policy/<int:pk>/", AdminPrivacyPolicyView.as_view(), name="admin-privacy-policy-detail"),
    path("privacy-policy/<int:pk>/toggle-active/", AdminPrivacyPolicyToggleActiveView.as_view(), name="admin-privacy-policy-toggle-active"),
]
