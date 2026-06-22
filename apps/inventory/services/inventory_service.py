from __future__ import annotations

import logging

from apps.core.exceptions import ApplicationError
from apps.inventory.interfaces.inventory_repository_interface import IInventoryRepository
from apps.inventory.models import StockEntry

logger = logging.getLogger(__name__)


class InventoryService:

    def __init__(self, repository: IInventoryRepository) -> None:
        self._repo = repository

    def get_product_stock(self, product_id: int) -> list:
        return self._repo.get_stock_for_product(product_id)

    def get_all_stock(self) -> list:
        return self._repo.get_all_snapshots()

    def get_product_history(self, product_id: int) -> list:
        return self._repo.get_entries_for_product(product_id)

    def record_stock_in(self, product_id: int, size_id: int, colour_id: int, quantity: int, note: str, recorded_by) -> object:
        if quantity <= 0:
            raise ApplicationError(
                message="Validation failed",
                errors={"quantity": ["Quantity must be greater than zero for a stock-in entry."]},
            )
        self._repo.assert_sku_belongs_to_product(product_id, size_id, colour_id)
        return self._repo.adjust_stock(
            product_id=product_id,
            size_id=size_id,
            colour_id=colour_id,
            quantity=quantity,
            movement_type=StockEntry.MovementType.IN,
            note=note,
            recorded_by=recorded_by,
        )

    def record_stock_out(self, product_id: int, size_id: int, colour_id: int, quantity: int, note: str, recorded_by) -> object:
        if quantity <= 0:
            raise ApplicationError(
                message="Validation failed",
                errors={"quantity": ["Quantity must be greater than zero for a stock-out entry."]},
            )
        self._repo.assert_sku_belongs_to_product(product_id, size_id, colour_id)
        snapshot = self._repo.get_stock(product_id, size_id, colour_id)
        if snapshot is None or snapshot.quantity_on_hand < quantity:
            available = snapshot.quantity_on_hand if snapshot else 0
            raise ApplicationError(
                message="Insufficient stock",
                errors={"quantity": [f"Requested {quantity} but only {available} units available."]},
            )
        return self._repo.adjust_stock(
            product_id=product_id,
            size_id=size_id,
            colour_id=colour_id,
            quantity=quantity,
            movement_type=StockEntry.MovementType.OUT,
            note=note,
            recorded_by=recorded_by,
        )

    def record_adjustment(self, product_id: int, size_id: int, colour_id: int, quantity: int, note: str, recorded_by) -> object:
        if quantity < 0:
            raise ApplicationError(
                message="Validation failed",
                errors={"quantity": ["Adjusted quantity cannot be negative."]},
            )
        self._repo.assert_sku_belongs_to_product(product_id, size_id, colour_id)
        return self._repo.adjust_stock(
            product_id=product_id,
            size_id=size_id,
            colour_id=colour_id,
            quantity=quantity,
            movement_type=StockEntry.MovementType.ADJUSTMENT,
            note=note,
            recorded_by=recorded_by,
        )
