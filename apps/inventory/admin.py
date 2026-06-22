from django.contrib import admin

from apps.inventory.models import InventorySnapshot, StockEntry


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "size", "colour", "movement_type", "quantity", "recorded_by", "created_at"]
    list_filter = ["movement_type", "product"]
    search_fields = ["product__name", "note"]
    readonly_fields = ["created_at"]


@admin.register(InventorySnapshot)
class InventorySnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "size", "colour", "quantity_on_hand", "updated_at"]
    list_filter = ["product"]
    search_fields = ["product__name"]
    readonly_fields = ["updated_at"]
