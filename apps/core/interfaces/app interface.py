from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

class IAppInterface(ABC):
    @abstractmethod
    def get_all(self) -> List[object]:
        """Return all instances."""

    @abstractmethod
    def get_all_active(self) -> List[object]:
        """Return all active instances."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[object]:
        """Return instances by PK, or None."""
    @abstractmethod
    def create(self, data: dict) -> object:
        """Create a new record."""

    @abstractmethod
    def update(self, id: int, data: dict) -> object:
        """Update an existing record."""
    @abstractmethod
    def delete(self, id: int) -> None:
        """Delete an existing record."""

    @abstractmethod
    def toggle_active(self, id: int) -> bool:
        """Toggle the active status of an existing record."""

    @abstractmethod
    def get_translation(
        self,id: int, language: str) -> Optional["Translation"]:
        """Return the translation row for (id, language), or None if absent."""

    @abstractmethod
    def upsert_translation(
        self,
        id: int,
        language: str,
        **kwargs
    ) -> "Translation":
        """Create or update the translation for (id, language)."""

