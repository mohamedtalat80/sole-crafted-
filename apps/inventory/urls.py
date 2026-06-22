from django.urls import path

from apps.inventory.views import (
    AdminInventoryListView,
    AdminProductStockHistoryView,
    AdminProductStockView,
    AdminStockAdjustmentView,
    AdminStockInView,
    AdminStockOutView,
)

public_inventory_urlpatterns: list = []

admin_inventory_urlpatterns = [
    path("inventory/", AdminInventoryListView.as_view(), name="admin-inventory-list"),
    path("inventory/stock-in/", AdminStockInView.as_view(), name="admin-inventory-stock-in"),
    path("inventory/stock-out/", AdminStockOutView.as_view(), name="admin-inventory-stock-out"),
    path("inventory/adjustment/", AdminStockAdjustmentView.as_view(), name="admin-inventory-adjustment"),
    path("inventory/products/<int:product_id>/stock/", AdminProductStockView.as_view(), name="admin-product-stock"),
    path("inventory/products/<int:product_id>/history/", AdminProductStockHistoryView.as_view(), name="admin-product-stock-history"),
]
