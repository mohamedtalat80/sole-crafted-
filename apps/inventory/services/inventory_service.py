from apps.inventory.interfaces.inventory_repository_interface import IInventoryRepository
from typing import List, Optional
from apps.inventory.models import InventorySnapshot, StockEntry
from apps.products.models import Product,Size,Colour
from django.conf import settings
from django.db import IntegrityError,transaction
from apps.core.exceptions import ConflictError, NotFoundError
import logging
logger = logging.getLogger(__name__)

class InventoryService:
    def __init__(self, repository: IInventoryRepository):
        self._repo = repository

    def get_stock(self,product_id:int,size_id:int,colour_id:int)->Optional[int]:
        return self._repo.get_stock(product_id,size_id,colour_id)
    def get_stock_for_product(self,product_id:int)->Optional[int]:
        return self._repo.get_stock_for_product(product_id)
    def get_product_stock(self,product_id:int)->List[InventorySnapshot]:
        return self._repo.get_product_stock(product_id)
    def get_all_snapshots(self)->List[InventorySnapshot]:
        return self._repo.get_all_snapshots()
    def get_entries_for_product(self,product_id:int)->List[StockEntry]:
        return self._repo.get_entries_for_product(product_id)
    def check_availability(self, product_id, size_id, colour_id, quantity) -> bool:
        return self._repo.check_availability(product_id,size_id,colour_id,quantity)
    def stock_in(self, product_id, size_id, colour_id, quantity, recorded_by, note):
        if quantity<=0:
            raise ValidationError("Quantity must be greater than 0")
        self._repo.assert_SKU_belongs_to_product(product_id,size_id,colour_id)
        self._repo.adjust_stock(product_id,size_id,colour_id,"in",quantity,recorded_by,note)
    
    def stock_out(self, product_id, size_id, colour_id, quantity, recorded_by, note):
        if quantity<=0:
            raise ValidationError("Quantity must be greater than 0")
        self._repo.assert_SKU_belongs_to_product(product_id,size_id,colour_id)
        snapshot=self._repo.get_stock(product_id,size_id,colour_id)
        if snapshot<quantity:
            raise ConflictError(f"Insufficient stock of {quantity} available {snapshot}")
        self._repo.adjust_stock(product_id,size_id,colour_id,"out",quantity,recorded_by,note)
    def stock_adjustment(self, product_id, size_id, colour_id, quantity, recorded_by, note):
        if quantity<0:
            raise ValidationError("Quantity must be greater than 0")
        self._repo.adjust_stock(product_id,size_id,colour_id,"adjustment",quantity,recorded_by,note)
    def assert_SKU_belongs_to_product(self,product_id,size_id,colour_id):
        self._repo.assert_SKU_belongs_to_product(product_id,size_id,colour_id)
    def reserve_stock(self, product_id, size_id, colour_id, quantity, order_ref, recorded_by):
        if quantity<=0:
            raise ValidationError("Quantity must be greater than 0")
        self._repo.assert_SKU_belongs_to_product(product_id,size_id,colour_id)
        snapshot=self._repo.get_stock(product_id,size_id,colour_id)
        if snapshot<quantity:
            raise ConflictError(f"Insufficient stock of {quantity} available {snapshot}")
        self._repo.reserve_stock(product_id,size_id,colour_id,quantity,order_ref,recorded_by)
    def release_stock(self, product_id, size_id, colour_id, quantity, order_ref, recorded_by):
        if quantity<=0:
            raise ValidationError("Quantity must be greater than 0")
        self._repo.assert_SKU_belongs_to_product(product_id,size_id,colour_id)
        self._repo.release_stock(product_id,size_id,colour_id,quantity,order_ref,recorded_by) 