from django.urls import path
from .views import UserRegistrationView, UserLoginView

urlpatterns = [
    path('signup/', UserRegistrationView.as_view(), name='user-signup'),
    path('signin/', UserLoginView.as_view(), name='user-signin'),
] 