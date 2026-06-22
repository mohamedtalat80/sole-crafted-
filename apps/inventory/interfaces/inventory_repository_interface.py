from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class IInventoryRepository(ABC):

    @abstractmethod
    def get_stock(self, product_id: int, size_id: int, colour_id: int) -> Optional[object]:
        """Return the InventorySnapshot for (product, size, colour), or None."""

    @abstractmethod
    def get_stock_for_product(self, product_id: int) -> List[object]:
        """Return all InventorySnapshot rows for a product."""

    @abstractmethod
    def get_all_snapshots(self) -> List[object]:
        """Return all InventorySnapshot rows (admin use)."""

    @abstractmethod
    def adjust_stock(
        self,
        product_id: int,
        size_id: int,
        colour_id: int,
        quantity: int,
        movement_type: str,
        note: str,
        recorded_by,
    ) -> object:
        """
        Record a StockEntry and update (or create) the matching InventorySnapshot.
        Returns the updated InventorySnapshot.
        """

    @abstractmethod
    def get_entries_for_product(self, product_id: int) -> List[object]:
        """Return all StockEntry rows for a product, newest first."""

    @abstractmethod
    def assert_sku_belongs_to_product(self, product_id: int, size_id: int, colour_id: int) -> None:
        """
        Raise ApplicationError if size_id or colour_id is not declared on the product's
        M2M sets (product.sizes / product.colors). This enforces that you can only stock
        combinations the product catalogue explicitly declares.
        """
