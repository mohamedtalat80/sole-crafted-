from django.urls import path
from apps.cookies_policy.views import (
    AdminCookiesPolicyListCreateView, AdminCookiesPolicyView, AdminCookiesPolicyToggleActiveView,
    CookiesPolicyView,
)

# public facing
public_cookies_policy_urlpatterns = [
    path("", CookiesPolicyView.as_view(), name="CookiesPolicy"),
]

# Admin-facing
admin_cookies_policy_urlpatterns = [
    path("cookies-policy/", AdminCookiesPolicyListCreateView.as_view(), name="admin-CookiesPolicy"),
    path("cookies-policy/<int:pk>/", AdminCookiesPolicyView.as_view(), name="admin-CookiesPolicy-detail"),
    path("cookies-policy/<int:pk>/toggle-active/", AdminCookiesPolicyToggleActiveView.as_view(), name="admin-CookiesPolicy-toggle-active"),
]
