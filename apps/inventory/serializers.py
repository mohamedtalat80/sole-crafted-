from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers import StrictModelSerializer, StrictSerializer
from apps.inventory.models import InventorySnapshot, StockEntry


class StockAdjustmentWriteSerializer(StrictSerializer):
    """Input for stock-in, stock-out, and adjustment endpoints."""

    product_id = serializers.IntegerField(min_value=1)
    size_id = serializers.IntegerField(min_value=1)
    colour_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class InventorySnapshotSerializer(StrictModelSerializer):
    """Current on-hand stock per product/size/colour."""

    product = serializers.StringRelatedField()
    size = serializers.StringRelatedField()
    colour = serializers.StringRelatedField()

    class Meta:
        model = InventorySnapshot
        fields = ["id", "product", "size", "colour", "quantity_on_hand", "updated_at"]


class StockEntrySerializer(StrictModelSerializer):
    """History log entry."""

    product = serializers.StringRelatedField()
    size = serializers.StringRelatedField()
    colour = serializers.StringRelatedField()
    recorded_by = serializers.StringRelatedField()

    class Meta:
        model = StockEntry
        fields = ["id", "product", "size", "colour", "movement_type", "quantity", "note", "recorded_by", "created_at"]
