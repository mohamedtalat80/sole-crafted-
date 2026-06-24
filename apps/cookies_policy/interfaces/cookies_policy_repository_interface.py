from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List


class ICookiesPolicyRepository(ABC):

    @abstractmethod
    def get_all(self) -> List[object]:
        """Return all CookiesPolicyS instances for the given profile."""

    @abstractmethod
    def get_all_active(self) -> List[object]:
        """Return all active CookiesPolicy instances."""

    @abstractmethod
    def get_by_id(self, cookies_policy_id: int) -> Optional[object]:
        """Return CookiesPolicy by PK (with select_related owner__user), or None."""
    @abstractmethod
    def create(self, data: dict) -> object:
        """Create a new CookiesPolicy record."""

    @abstractmethod
    def update(self, cookies_policy_id: int, data: dict, updated_by) -> object:
        """Update an existing CookiesPolicy record."""
    @abstractmethod
    def delete(self, cookies_policy) -> None:
        """Delete an existing CookiesPolicy record."""

    @abstractmethod
    def toggle_active(self, cookies_policy) -> bool:
        """Toggle the active status of an existing CookiesPolicy record."""

    @abstractmethod
    def get_translation(
        self, cookies_policy, language: str) -> Optional["CookiesPolicyTranslation"]:
        """Return the translation row for (cookies_policy, language), or None if absent."""

    @abstractmethod
    def upsert_translation(
        self,
        cookies_policy,
        language: str,
        title: str,
        content: str,
    ) -> "CookiesPolicyTranslation":
        """Create or update the translation for (cookies_policy, language)."""

