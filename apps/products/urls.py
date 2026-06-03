from django.urls import path

from apps.products.views import ProductDetailView, ProductListView

public_products_urlpatterns = [
    path("", ProductListView.as_view(), name="product-list"),
    path("<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
]

admin_products_urlpatterns: list = []
