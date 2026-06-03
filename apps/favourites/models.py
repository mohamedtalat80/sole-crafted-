from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.products.models import Product


class Favourite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favourites")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="favourited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        verbose_name = "Favourite"
        verbose_name_plural = "Favourites"

    def __str__(self) -> str:
        return f"{self.user} — {self.product.name}"
