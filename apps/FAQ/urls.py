from django.urls import path
from apps.FAQ.views import (
    AdminOwnerFAQListView, AdminOwnerFAQView, AdminOwnerFAQToggleActiveView,
    AdminCustomerFAQListView, AdminCustomerFAQView, AdminCustomerFAQToggleActiveView,
    FAQOwnerListView, FAQCustomerListView,
)

# public facing
public_FAQ_urlpatterns = [
    path("owner/", FAQOwnerListView.as_view(), name="owner-FAQ"),
    path("customer/", FAQCustomerListView.as_view(), name="customer-FAQ"),
]

# Admin-facing
admin_FAQ_urlpatterns = [
    path("FAQ/owner/", AdminOwnerFAQListView.as_view(), name="admin-owner-FAQ"),
    path("FAQ/owner/<int:pk>/", AdminOwnerFAQView.as_view(), name="admin-owner-FAQ-detail"),
    path("FAQ/owner/<int:pk>/toggle-active/", AdminOwnerFAQToggleActiveView.as_view(), name="admin-owner-FAQ-toggle-active"),
    path("FAQ/customer/", AdminCustomerFAQListView.as_view(), name="admin-customer-FAQ"),
    path("FAQ/customer/<int:pk>/", AdminCustomerFAQView.as_view(), name="admin-customer-FAQ-detail"),
    path("FAQ/customer/<int:pk>/toggle-active/", AdminCustomerFAQToggleActiveView.as_view(), name="admin-customer-FAQ-toggle-active"),
]
