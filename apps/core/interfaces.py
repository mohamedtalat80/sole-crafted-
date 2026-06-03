from abc import ABC, abstractmethod

class IGlobalRepository(ABC):
    @abstractmethod
    def get_all(self) -> dict:
        """Fetch all data for the application."""
        pass
    def get_all_active(self) -> dict:
        """Fetch all active records."""
        pass
    def get_by_id(self, id: int) -> dict:
        """Fetch a single record by its ID."""
        pass
    def create(self, data: dict) -> dict:
        """Create a new record with the provided data."""
        pass
    def update(self, id: int, data: dict) -> dict:
        """Update an existing record by its ID with the provided data."""
        pass
    def delete(self, object: object) -> bool:
        """Delete a record by its ID."""
        pass
    def toggle_active(self,object:object) -> dict:
        """Toggle the active status of a record by its ID."""
        pass
    def get_transltions(self, id: int) -> dict:
        """Fetch translations for a record by its ID."""
        pass    
    def upsert_translation(self, id: int, language_code: str, data: dict) -> dict:
        """Upsert a translation for a record by its ID and language code."""
        pass