import django
from django.contrib import admin
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.users.urls import urlpatterns as user_urlpatterns, admin_urlpatterns as admin_user_urlpatterns
from apps.privacy_policy.urls import public_privacy_policy_urlpatterns, admin_privacy_policy_urlpatterns
from apps.terms_and_conditions.urls import public_TermsAndConditions_urlpatterns, admin_TermsAndConditions_urlpatterns
from apps.FAQ.urls import public_FAQ_urlpatterns, admin_FAQ_urlpatterns
from apps.contact_us.urls import public_contact_us_urlpatterns, admin_contact_us_urlpatterns
from apps.products.urls import public_products_urlpatterns, admin_products_urlpatterns
from apps.inventory.urls import public_inventory_urlpatterns, admin_inventory_urlpatterns
from apps.cookies_policy.urls import public_cookies_policy_urlpatterns, admin_cookies_policy_urlpatterns

_CTX = {"django_version": django.get_version()}


@require_http_methods(["GET", "POST"])
def portal(request):
    """Root: redirect to dashboard if already authenticated, else show login."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect("dashboard")
        error = "Invalid credentials or insufficient permissions."

    return render(request, "landing.html", {**_CTX, "error": error})


@staff_member_required(login_url="/")
def dashboard(request):
    return render(request, "dashboard.html", {
        **_CTX,
        "username": request.user.get_username(),
    })

def portal_logout(request):
    logout(request)
    return redirect("/")
    

urlpatterns = [
    path("", portal, name="portal"),
    path("dashboard/", dashboard, name="dashboard"),
    path("logout/", portal_logout, name="portal-logout"),
    path('admin/', admin.site.urls),

    # API schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Auth / users
    path('api/auth/', include(user_urlpatterns)),

    # Public endpoints
    path('api/privacy-policy/', include(public_privacy_policy_urlpatterns)),
    path('api/cookies-policy/', include(public_cookies_policy_urlpatterns)),
    path('api/terms-and-conditions/', include(public_TermsAndConditions_urlpatterns)),
    path('api/faq/', include(public_FAQ_urlpatterns)),
    path('api/contact-us/', include(public_contact_us_urlpatterns)),
    path('api/products/', include(public_products_urlpatterns)),
    path('api/inventory/', include(public_inventory_urlpatterns)),

    # Admin endpoints
    path('api/admin/', include((admin_user_urlpatterns+
        admin_privacy_policy_urlpatterns+
        admin_cookies_policy_urlpatterns+
        admin_TermsAndConditions_urlpatterns+
        admin_FAQ_urlpatterns+
        admin_contact_us_urlpatterns+
        admin_products_urlpatterns+
        admin_inventory_urlpatterns,
        "admin_endpoints"
    ))),
    
   
]
