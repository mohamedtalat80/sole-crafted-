from django.urls import path
from .views import UserProfileView,UserInfoView 

urlpatterns = [
    path('', UserProfileView.as_view(), name='user-profile'),
    path('info/', UserInfoView.as_view(), name='user-info'),
]