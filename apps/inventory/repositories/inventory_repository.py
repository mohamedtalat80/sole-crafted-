from __future__ import annotations

from typing import List, Optional

from django.db import transaction

from apps.core.exceptions import ApplicationError, NotFoundError
from apps.inventory.interfaces.inventory_repository_interface import IInventoryRepository
from apps.inventory.models import InventorySnapshot, StockEntry
from apps.products.models import Colour, Product, Size


class InventoryRepository(IInventoryRepository):

    def get_stock(self, product_id: int, size_id: int, colour_id: int) -> Optional[InventorySnapshot]:
        try:
            return InventorySnapshot.objects.select_related("product", "size", "colour").get(
                product_id=product_id, size_id=size_id, colour_id=colour_id
            )
        except InventorySnapshot.DoesNotExist:
            return None

    def get_stock_for_product(self, product_id: int) -> List[InventorySnapshot]:
        self._assert_product_exists(product_id)
        return (
            InventorySnapshot.objects.filter(product_id=product_id)
            .select_related("product", "size", "colour")
            .order_by("size__name", "colour__name")
        )

    def get_all_snapshots(self) -> List[InventorySnapshot]:
        return (
            InventorySnapshot.objects.all()
            .select_related("product", "size", "colour")
            .order_by("product__name", "size__name", "colour__name")
        )

    @transaction.atomic
    def adjust_stock(
        self,
        product_id: int,
        size_id: int,
        colour_id: int,
        quantity: int,
        movement_type: str,
        note: str,
        recorded_by,
    ) -> InventorySnapshot:
        product = self._get_product(product_id)
        size = self._get_size(size_id)
        colour = self._get_colour(colour_id)

        StockEntry.objects.create(
            product=product,
            size=size,
            colour=colour,
            quantity=quantity,
            movement_type=movement_type,
            note=note,
            recorded_by=recorded_by,
        )

        snapshot, _ = InventorySnapshot.objects.select_for_update().get_or_create(
            product=product,
            size=size,
            colour=colour,
            defaults={"quantity_on_hand": 0},
        )

        if movement_type == StockEntry.MovementType.IN:
            snapshot.quantity_on_hand += quantity
        elif movement_type == StockEntry.MovementType.OUT:
            snapshot.quantity_on_hand -= quantity
        else:
            snapshot.quantity_on_hand = quantity

        snapshot.save()
        return snapshot

    def get_entries_for_product(self, product_id: int) -> List[StockEntry]:
        self._assert_product_exists(product_id)
        return (
            StockEntry.objects.filter(product_id=product_id)
            .select_related("product", "size", "colour", "recorded_by")
            .order_by("-created_at")
        )

    def assert_sku_belongs_to_product(self, product_id: int, size_id: int, colour_id: int) -> None:
        try:
            product = Product.objects.prefetch_related("sizes", "colors").get(pk=product_id)
        except Product.DoesNotExist:
            raise NotFoundError(message="Product not found")

        if not product.sizes.filter(pk=size_id).exists():
            raise ApplicationError(
                message="Invalid SKU",
                errors={"size_id": [f"Size {size_id} is not declared for product '{product.name}'. Add it to the product's sizes first."]},
            )
        if not product.colors.filter(pk=colour_id).exists():
            raise ApplicationError(
                message="Invalid SKU",
                errors={"colour_id": [f"Colour {colour_id} is not declared for product '{product.name}'. Add it to the product's colours first."]},
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assert_product_exists(self, product_id: int) -> None:
        if not Product.objects.filter(pk=product_id).exists():
            raise NotFoundError(message="Product not found")

    def _get_product(self, product_id: int) -> Product:
        try:
            return Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise NotFoundError(message="Product not found")

    def _get_size(self, size_id: int) -> Size:
        try:
            return Size.objects.get(pk=size_id)
        except Size.DoesNotExist:
            raise NotFoundError(message="Size not found")

    def _get_colour(self, colour_id: int) -> Colour:
        try:
            return Colour.objects.get(pk=colour_id)
        except Colour.DoesNotExist:
            raise NotFoundError(message="Colour not found")
