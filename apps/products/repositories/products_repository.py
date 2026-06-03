from __future__ import annotations

from apps.core.exceptions import NotFoundError
from apps.products.interfaces.products_repository_interface import IProductRepository
from apps.products.models import Product


class ProductRepository(IProductRepository):

    def get_all_available(self) -> list[Product]:
        return (
            Product.objects.filter(is_available=True)
            .select_related("category")
            .prefetch_related("tags", "images")
            .order_by("-created_at")
        )

    def get_by_id(self, product_id: int) -> Product:
        try:
            return (
                Product.objects.select_related("category")
                .prefetch_related("tags", "images")
                .get(pk=product_id)
            )
        except Product.DoesNotExist:
            raise NotFoundError(message="Product not found")

    def get_all(self) -> list[Product]:
        return (
            Product.objects.all()
            .select_related("category")
            .prefetch_related("tags", "images")
            .order_by("-created_at")
        )
