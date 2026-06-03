from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.products.models import Product


class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings")
    rating = models.IntegerField(default=0)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "user")

    def __str__(self) -> str:
        return f"{self.user} — {self.product.name} ({self.rating})"
