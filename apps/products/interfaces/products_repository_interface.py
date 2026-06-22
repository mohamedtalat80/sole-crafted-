from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class IProductRepository(ABC):

    @abstractmethod
    def get_all(self) -> List[object]:
        """Return all products."""

    @abstractmethod
    def get_all_active(self) -> List[object]:
        """Return all active products with related data prefetched."""

    @abstractmethod
    def get_by_id(self, id: int) -> object:
        """Return a Product by PK with related data prefetched, or raise NotFoundError."""

    @abstractmethod
    def get_by_category(self, category_id: int) -> List[object]:
        """Return all products in a category."""

    @abstractmethod
    def get_by_tag(self, tag_id: int) -> List[object]:
        """Return all products with a given tag."""

    @abstractmethod
    def create(self, data: dict) -> object:
        """Create and return a new Product."""

    @abstractmethod
    def update(self, id: int, data: dict) -> object:
        """Update and return an existing Product."""

    @abstractmethod
    def delete(self, id: int) -> None:
        """Delete a Product by PK."""

    @abstractmethod
    def toggle_active(self, id: int) -> bool:
        """Toggle is_active and return the new value."""

    @abstractmethod
    def filter(self, **kwargs) -> List[object]:
        """Return products matching the given ORM filter kwargs."""

    @abstractmethod
    def get_translation(self, instance, language: str) -> Optional[object]:
        """Return the ProductTranslation for (instance, language), or None."""

    @abstractmethod
    def upsert_translation(self, instance, language: str, name: str, description: str) -> object:
        """Create or update the translation for (instance, language)."""
