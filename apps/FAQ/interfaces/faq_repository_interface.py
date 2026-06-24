from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List


class IFAQRepository(ABC):

    @abstractmethod
    def get_all(self) -> List[object]:
        """Return all FAQS instances."""
    @abstractmethod
    def get_all_active(self) -> List[object]:
        """Return all active FAQS instances."""
    @abstractmethod
    def get_by_id(self, FAQ_id: int) -> Optional[object]:
        """Return FAQS by PK, or None."""
    @abstractmethod
    def create(self,data: dict) -> object:
        """Create a new FAQ record."""

    @abstractmethod
    def update(self, FAQ, data: dict) -> object:
        """Update an existing FAQS record."""
    @abstractmethod
    def delete(self, FAQ) -> None:
        """Delete an existing FAQS record."""
    @abstractmethod
    def toggle_active(self, FAQ) -> None:
        """Toggle the active status of an existing FAQ record."""

    @abstractmethod
    def get_translation(
        self,FAQ, language: str) -> Optional["FAQTranslation"]:
        """Return the translation row for (FAQ, language), or None if absent."""

    @abstractmethod
    def upsert_translation(
        self,
        FAQ,
        language: str,
        question: str,
        answer: str,
    ) -> "FAQTranslation":
        """Create or update the translation for (FAQ, language)."""

