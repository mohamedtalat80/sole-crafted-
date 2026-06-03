from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class IProductRepository(ABC):

    @abstractmethod
    def get_all_available(self) -> List[object]:
        """Return all available products."""

    @abstractmethod
    def get_by_id(self, product_id: int) -> object:
        """Return a Product by PK with related data prefetched, or raise NotFoundError."""

    @abstractmethod
    def get_all(self) -> List[object]:
        """Return all products (admin use)."""
