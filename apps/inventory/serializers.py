from rest_framework import serializers
from apps.core.serializers import StrictModelSerializer,StrictSerializer
from apps.inventory.models import InventorySnapshot, StockEntry
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

class StockAdjustmentSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    size_id = serializers.IntegerField(required=True)
    colour_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True)
    recorded_by = serializers.IntegerField(required=True)
    note = serializers.CharField(required=False, allow_blank=True)
class StockReserveSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    size_id = serializers.IntegerField(required=True)
    colour_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True)
    recorded_by = serializers.IntegerField(required=True)
    note = serializers.CharField(required=False, allow_blank=True)
class StockReleaseSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    size_id = serializers.IntegerField(required=True)
    colour_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True)
    recorded_by = serializers.IntegerField(required=True)
    note = serializers.CharField(required=False, allow_blank=True)

