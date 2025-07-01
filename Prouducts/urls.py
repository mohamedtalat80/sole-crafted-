from django.urls import path
from .views import HomeProductListView, ProductDetailsView
urlpatterns = [
    path('home-products/', HomeProductListView.as_view(), name='home-products'),
    path('products-details/<int:pk>/', ProductDetailsView.as_view(), name='product-details'),
]