from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List


class ITermsAndConditionsRepository(ABC):

    @abstractmethod
    def get_all(self) -> List[object]:
        """Return all TermsAndConditionsS instances for the given profile."""

    @abstractmethod
    def get_all_active(self) -> List[object]:
        """Return all active TermsAndConditions instances."""

    @abstractmethod
    def get_by_id(self, TermsAndConditions_id: int) -> Optional[object]:
        """Return TermsAndConditionsS by PK (with select_related owner__user), or None."""
    @abstractmethod
    def create(self, data: dict) -> object:
        """Create a new TermsAndConditions record."""

    @abstractmethod
    def update(self, TermsAndConditions, data: dict) -> object:
        """Update an existing TermsAndConditionsS record."""
    @abstractmethod
    def delete(self, TermsAndConditions) -> None:
        """Delete an existing TermsAndConditionsS record."""

    @abstractmethod
    def toggle_active(self, TermsAndConditions) -> None:
        """Toggle the active status of an existing TermsAndConditions record."""

    @abstractmethod
    def get_translation(
        self,TermsAndConditions, language: str) -> Optional["TermsAndConditionsTranslation"]:
        """Return the translation row for (TermsAndConditions, language), or None if absent."""

    @abstractmethod
    def upsert_translation(
        self,
        TermsAndConditions,
        language: str,
        question: str,
        answer: str,
    ) -> "TermsAndConditionsTranslation":
        """Create or update the translation for (TermsAndConditions, language)."""

