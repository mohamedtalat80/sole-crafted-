from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.products.views import (
    AdminCategoryViewSet,
    AdminColourViewSet,
    AdminProductViewSet,
    AdminSizeViewSet,
    AdminTagViewSet,
    ProductPublicListView,
)

_admin_router = SimpleRouter(trailing_slash=True)
_admin_router.register("products", AdminProductViewSet, basename="admin-product")
_admin_router.register("categories", AdminCategoryViewSet, basename="admin-category")
_admin_router.register("tags", AdminTagViewSet, basename="admin-tag")
_admin_router.register("colours", AdminColourViewSet, basename="admin-colour")
_admin_router.register("sizes", AdminSizeViewSet, basename="admin-size")

public_products_urlpatterns = [
    path("", ProductPublicListView.as_view(), name="product-list"),
]

admin_products_urlpatterns = [
    path("", include(_admin_router.urls)),
]
