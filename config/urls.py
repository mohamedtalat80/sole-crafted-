from django.contrib import admin
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

urlpatterns = [
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
    path('api/faq/owner/', include((public_FAQ_urlpatterns[:1], 'faq_owner'))),
    path('api/faq/customer/', include((public_FAQ_urlpatterns[1:], 'faq_customer'))),
    path('api/contact-us/', include(public_contact_us_urlpatterns)),
    path('api/products/', include(public_products_urlpatterns)),

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
