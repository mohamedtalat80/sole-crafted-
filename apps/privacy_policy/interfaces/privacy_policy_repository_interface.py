from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List


class IPrivacyPolicyRepository(ABC):

    @abstractmethod
    def get_all(self) -> List[object]:
        """Return all PrivacyPolicy instances ordered by display_order."""

    @abstractmethod
    def get_all_active(self) -> List[object]:
        """Return all active PrivacyPolicy instances with translations prefetched."""

    @abstractmethod
    def get_by_id(self, policy_id: int) -> Optional[object]:
        """Return PrivacyPolicy by PK with translations prefetched, or raise NotFoundError."""

    @abstractmethod
    def create(self, data: dict) -> object:
        """Create and return a new PrivacyPolicy record."""

    @abstractmethod
    def update(self, policy_id: int, data: dict, updated_by) -> object:
        """Update and return an existing PrivacyPolicy record."""

    @abstractmethod
    def delete(self, instance) -> None:
        """Delete an existing PrivacyPolicy record."""

    @abstractmethod
    def toggle_active(self, instance) -> bool:
        """Toggle is_active and return the new value."""

    @abstractmethod
    def get_translation(self, instance, language: str) -> Optional["PrivacyPolicyTranslation"]:
        """Return the translation row for (instance, language), or None if absent."""

    @abstractmethod
    def upsert_translation(
        self,
        instance,
        language: str,
        title: str,
        content: str,
    ) -> "PrivacyPolicyTranslation":
        """Create or update the translation for (instance, language). Returns the object."""

