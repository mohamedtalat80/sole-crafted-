from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List
from apps.inventory.models import InventorySnapshot

class IInventoryRepository(ABC):
    @abstractmethod
    def get_stock(self,product_id:int,size_id:int,colour_id:int)->Optional[int]:
        """Return the stock of a product."""
    @abstractmethod
    def get_stock_for_product(self,product_id:int)->Optional[int]:
        """Return the total stock of a product."""
    @abstractmethod
    def get_product_stock(self,product_id:int)->List[InventorySnapshot]:
        """Return the stock snapshots for a product."""
    @abstractmethod
    def get_all_snapshots(self)->List[InventorySnapshot]:
        """Return all snapshots."""
    @abstractmethod
    def get_entries_for_product(self,product_id:int)->List[InventoryEntry]:
        """Return all enteries for a product."""    
    
    @abstractmethod
    def check_availability(self, product_id, size_id, colour_id, quantity) -> bool:
        """Read-only check: returns True if enough stock exists."""
    @abstractmethod
    def adjust_stock(self, product_id, size_id, colour_id,movement_type, quantity, recorded_by, note):
        """Adjust stock of a product."""
    @abstractmethod
    def assert_SKU_belongs_to_product(self, product_id, size_id, colour_id):
        """Assert that a SKU belongs to a product."""
    @abstractmethod
    def reserve_stock(self, product_id, size_id, colour_id, quantity, order_ref, recorded_by):
        """
        Atomically checks AND deducts stock for a confirmed order.
        Raises ApplicationError if insufficient.
        Records a StockEntry(OUT, note=f"Order #{order_ref}").
        """

    @abstractmethod
    def release_stock(self, product_id, size_id, colour_id, quantity, order_ref, recorded_by):
        """
        Returns stock when an order is cancelled.
        Records a StockEntry(IN, note=f"Cancelled Order #{order_ref}").
        """
        