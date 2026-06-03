from __future__ import annotations

import logging

from apps.products.interfaces.products_repository_interface import IProductRepository
from apps.products.models import Product

logger = logging.getLogger(__name__)


class ProductService:

    def __init__(self, repository: IProductRepository) -> None:
        self._repo = repository

    def list_available_products(self) -> list[Product]:
        return self._repo.get_all_available()

    def get_product(self, product_id: int) -> Product:
        return self._repo.get_by_id(product_id)

    def list_all_products(self) -> list[Product]:
        return self._repo.get_all()
