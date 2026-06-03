from django.urls import path
from apps.contact_us.views import (
    UserContactMessageView,
    AdminContactMessageDetailView,
    AdminContactMessageListView,
    PublicContactContentListView,
    AdminContactContentView,
    
)

admin_contact_us_urlpatterns = [
    path('contact_us/messages/', AdminContactMessageListView.as_view(), name='admin-contact-message-list'),
    path('contact_us/messages/<int:id>/', AdminContactMessageDetailView.as_view(), name='admin-contact-message-detail'),
    path('contact_us/content/', AdminContactContentView.as_view(), name='admin-contact-content'),
]
public_contact_us_urlpatterns = [
    path('', UserContactMessageView.as_view(), name='user-contact-message'),
    path('content/', PublicContactContentListView.as_view(), name='public-contact-content'),
]
