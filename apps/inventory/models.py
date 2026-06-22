from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.products.models import Product, Size, Colour


class StockEntry(models.Model):
    """Tracks the quantity of a specific product/size/colour combination."""

    class MovementType(models.TextChoices):
        IN = "in", "Stock In"
        OUT = "out", "Stock Out"
        ADJUSTMENT = "adjustment", "Adjustment"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_entries")
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name="stock_entries")
    colour = models.ForeignKey(Colour, on_delete=models.CASCADE, related_name="stock_entries")
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    note = models.TextField(blank=True, default="")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stock Entry"
        verbose_name_plural = "Stock Entries"

    def __str__(self) -> str:
        return f"{self.get_movement_type_display()} | {self.product.name} | {self.size.name} / {self.colour.name} | qty={self.quantity}"


class InventorySnapshot(models.Model):
    """
    Current on-hand quantity per product/size/colour.
    Updated in-place by the service every time a StockEntry is recorded.
    Never written directly — always managed through the service.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="inventory")
    size = models.ForeignKey(Size, on_delete=models.CASCADE, related_name="inventory")
    colour = models.ForeignKey(Colour, on_delete=models.CASCADE, related_name="inventory")
    quantity_on_hand = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "size", "colour")
        ordering = ["product", "size", "colour"]
        verbose_name = "Inventory Snapshot"
        verbose_name_plural = "Inventory Snapshots"

    def __str__(self) -> str:
        return f"{self.product.name} | {self.size.name} / {self.colour.name} | on-hand={self.quantity_on_hand}"
