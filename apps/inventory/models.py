from django.db import models
from apps.products.models import Product,Size,Colour
from django.conf import settings
class StockEntry(models.Model):
    MOVEMENT_CHOICES = [
        ('in', 'IN'),
        ('out', 'OUT'),
        ('adjustment', 'ADJUSTMENT'),
    ]
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE,related_name="stock_entries")
    size_id = models.ForeignKey(Size, on_delete=models.CASCADE,related_name="stock_entries")
    colour_id = models.ForeignKey(Colour, on_delete=models.CASCADE,related_name="stock_entries")
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_CHOICES)
    quantity = models.IntegerField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name="stock_entries")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.product_id} {self.size_id} {self.colour_id} {self.movement_type} {self.quantity}"

class InventorySnapshot(models.Model):
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE,related_name="inventory_snapshots")
    size_id = models.ForeignKey(Size, on_delete=models.CASCADE,related_name="inventory_snapshots")
    colour_id = models.ForeignKey(Colour, on_delete=models.CASCADE,related_name="inventory_snapshots")
    quantity_on_hand = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.product_id} {self.size_id} {self.colour_id} {self.quantity}"