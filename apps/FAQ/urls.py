from django.urls import path
from apps.FAQ.views import (
    AdminFAQListView, AdminFAQView, AdminFAQToggleActiveView,
    FAQListView 
)

# public facing
public_FAQ_urlpatterns = [
    path("", FAQListView.as_view(), name="FAQ"),
]

# Admin-facing
admin_FAQ_urlpatterns = [
    path("", AdminFAQListView.as_view(), name="admin-FAQ"),
    path("<int:pk>/", AdminFAQView.as_view(), name="admin-FAQ-detail"),
    path("<int:pk>/toggle-active/", AdminFAQToggleActiveView.as_view(), name="admin-FAQ-toggle-active"),
]
