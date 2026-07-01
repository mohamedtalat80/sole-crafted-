from django.urls import path

from apps.inventory.views import (
    AdminInventoryListView,
    AdminProductStockView,
    AdminProductStockHistoryView,
    AdminStockInView,
    AdminStockOutView,
    AdminStockAdjustmentView,
)

public_inventory_urlpatterns = [
    # No public endpoints currently
]

admin_inventory_urlpatterns = [
    path('list/', AdminInventoryListView.as_view(), name='admin-inventory-list'),
    path('product/<int:product_id>/', AdminProductStockView.as_view(), name='admin-product-stock'),
    path('product/<int:product_id>/history/', AdminProductStockHistoryView.as_view(), name='admin-product-stock-history'),
    path('in/', AdminStockInView.as_view(), name='admin-stock-in'),
    path('out/', AdminStockOutView.as_view(), name='admin-stock-out'),
    path('adjust/', AdminStockAdjustmentView.as_view(), name='admin-stock-adjust'),
]
