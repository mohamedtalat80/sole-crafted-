from apps.inventory.interfaces.inventory_repository_interface import IInventoryRepository
from apps.inventory.models import InventorySnapshot, StockEntry
from apps.products.models import Product,Size,Colour
from django.conf import settings
from django.db import IntegrityError,transaction,models
from apps.core.exceptions import ConflictError
from typing import Optional, List

class InventoryRepository(IInventoryRepository):
    def get_stock(self,product_id:int,size_id:int,colour_id:int)->Optional[int]:
        try:
            return InventorySnapshot.objects.select_related('product','size','colour').get(product_id=product_id,size_id=size_id,colour_id=colour_id).quantity
        except InventorySnapshot.DoesNotExist:
            return None
    def get_stock_for_product(self,product_id:int)->Optional[int]:
        self._assert_products_exist(product_id)
        result = InventorySnapshot.objects.filter(product_id=product_id).aggregate(total=models.Sum('quantity_on_hand'))
        return result['total'] if result['total'] is not None else 0
    def get_product_stock(self,product_id:int)->List[InventorySnapshot]:
        self._assert_products_exist(product_id)
        return InventorySnapshot.objects.select_related('product','size','colour').filter(product_id=product_id)
    def get_all_snapshots(self)->List[InventorySnapshot]:
        return InventorySnapshot.objects.select_related('product','size','colour').all()
    def get_entries_for_product(self,product_id:int)->List[StockEntry]:
        self._assert_products_exist(product_id)
        try:
            return StockEntry.objects.select_related('product','size','colour').filter(product_id=product_id)
        except StockEntry.DoesNotExist:
            return None
    def check_availability(self, product_id, size_id, colour_id, quantity) -> bool:
        try:
            return InventorySnapshot.objects.select_related('product','size','colour').get(product_id=product_id,size_id=size_id,colour_id=colour_id).quantity >= quantity
        except InventorySnapshot.DoesNotExist:
            return False
    @transaction.atomic
    def adjust_stock(
        self,
        product_id,
        size_id,
        colour_id,
        movement_type,
        quantity,
        recorded_by,
        note
         ):
        product=self._get_product(product_id)
        size=self._get_size(size_id)
        colour=self._get_colour(colour_id)
        StockEntry.objects.create(
            product=product,
            size=size,
            colour=colour,
            movement_type=movement_type,
            quantity=quantity,
            recorded_by=recorded_by,
            note=note
        )
        
        snapshot=InventorySnapshot.objects.select_for_update().get_or_create(
            product=product,
            size=size,
            colour=colour,
            defaults={'quantity_on_hand': 0}
        )
        
        
        if movement_type=="in":
            snapshot.quantity_on_hand+=quantity
        elif movement_type=="out":
            snapshot.quantity_on_hand-=quantity
        elif movement_type=="adjustment":
            snapshot.quantity_on_hand=quantity
        snapshot.save()
    def assert_SKU_belongs_to_product(self,product_id,size_id,colour_id):
        product=self._get_product(product_id)
        if not product.sizes.filter(id=size_id).exists():
            raise ConflictError("Size does not belong to product")
        if not product.colours.filter(id=colour_id).exists():
            raise ConflictError("Colour does not belong to product")
    
    def reserve_stock(self, product_id, size_id, colour_id, quantity, order_ref, recorded_by):
        with transaction.atomic():
            snapshot = InventorySnapshot.objects.select_for_update().get(
                product_id=product_id,
                size_id=size_id,
                colour_id=colour_id
            )
            
            if snapshot.quantity_on_hand < quantity:
                raise ConflictError("Insufficient stock available for reservation")
            
            snapshot.quantity_on_hand -= quantity
            snapshot.save()
            
            StockEntry.objects.create(
                product_id=product_id,
                size_id=size_id,
                colour_id=colour_id,
                movement_type='out',
                quantity=quantity,
                recorded_by=recorded_by,
                note=f"Reserved for Order #{order_ref}"
            )
    def release_stock(self, product_id, size_id, colour_id, quantity, order_ref, recorded_by):
        with transaction.atomic():
            snapshot = InventorySnapshot.objects.select_for_update().get(
                product_id=product_id,
                size_id=size_id,
                colour_id=colour_id
            )
            
            snapshot.quantity_on_hand += quantity
            snapshot.save()
            
            StockEntry.objects.create(
                product_id=product_id,
                size_id=size_id,
                colour_id=colour_id,
                movement_type='in',
                quantity=quantity,
                recorded_by=recorded_by,
                note=f"Released from Order #{order_ref}"
            )

    #helpers methods 
    def _assert_products_exist(self,product_id:int):
        if not Product.objects.filter(id=product_id).exists():
            raise ConflictError("Product does not exist") 
    def _get_product(self,product_id:int)->Product:
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ConflictError("Product does not exist") 
    def _get_size(self,size_id:int)->Size:
        try:
            return Size.objects.get(id=size_id)
        except Size.DoesNotExist:
            raise ConflictError("Size does not exist") 
    def _get_colour(self,colour_id:int)->Colour:
        try:
            return Colour.objects.get(id=colour_id)
        except Colour.DoesNotExist:
            raise ConflictError("Colour does not exist") 
