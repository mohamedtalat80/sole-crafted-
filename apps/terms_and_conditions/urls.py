from django.urls import path
from apps.terms_and_conditions.views import (
    AdminTermsAndConditionsListCreateView, AdminTermsAndConditionsView, AdminTermsAndConditionsToggleActiveView,
    TermsAndConditionsView,
)

# public facing
public_TermsAndConditions_urlpatterns = [
    path("", TermsAndConditionsView.as_view(), name="TermsAndConditions"),
]

# Admin-facing
admin_TermsAndConditions_urlpatterns = [
    path("termsandconditions/", AdminTermsAndConditionsListCreateView.as_view(), name="admin-TermsAndConditions"),
    path("termsandconditions/<int:pk>/", AdminTermsAndConditionsView.as_view(), name="admin-TermsAndConditions-detail"),
    path("termsandconditions/<int:pk>/toggle-active/", AdminTermsAndConditionsToggleActiveView.as_view(), name="admin-TermsAndConditions-toggle-active"),
]
