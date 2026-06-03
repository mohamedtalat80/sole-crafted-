from __future__ import annotations

from apps.core.exceptions import ConflictError, NotFoundError
from apps.terms_and_conditions.interfaces.terms_and_conditions_repository_interface import ITermsAndConditionsRepository
from apps.terms_and_conditions.models import TermsAndConditions
from apps.core.utils.translation_utils import TRANSLATION_LANGUAGES,TranslationService
import logging
from django.conf import settings
User=settings.AUTH_USER_MODEL
logger = logging.getLogger(__name__)
class TermsAndConditionsService:    

    def __init__(self, repository: ITermsAndConditionsRepository,translation:TranslationService) -> None:
        self._repo = repository
        self._translation = translation
    def get_all_terms_and_conditions(self) -> list:
        return self._repo.get_all()

    def get_all_active_terms_and_conditions(self) -> list:
        return self._repo.get_all_active()

    def get_TermsAndConditions_by_id(self, TermsAndConditions_id: int) -> "TermsAndConditions":
        TermsAndConditions = self._repo.get_by_id(TermsAndConditions_id)
        if TermsAndConditions is None:
            raise NotFoundError(message="TermsAndConditions not found")
        return TermsAndConditions

    def add_TermsAndConditions(self, data: dict) -> "TermsAndConditions":
        display_order = data.get("display_order")
        if display_order is not None and TermsAndConditions.objects.filter(display_order=display_order).exists():
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": [f"Display order {display_order} is already used by another Terms and Conditions entry."]},
            )
        instance = self._repo.create(data)
        self._auto_translate_all(instance)
        return instance

    def update_TermsAndConditions(self, TermsAndConditions_id: int, data: dict,updated_by:User) -> "TermsAndConditions":
        display_order = data.get("display_order")
        if display_order is not None and TermsAndConditions.objects.filter(display_order=display_order).exclude(id=TermsAndConditions_id).exists():
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": [f"Display order {display_order} is already used by another Terms and Conditions entry."]},
            )
        instance = self._repo.update(TermsAndConditions_id, data,updated_by)
        if "title" in data or "content" in data:
            self._auto_translate_all(instance)
        return instance

    def delete_TermsAndConditions(self, TermsAndConditions_id: int) -> None:
        TermsAndConditions = self.get_TermsAndConditions_by_id(TermsAndConditions_id)
        self._repo.delete(TermsAndConditions)

    def toggle_active_TermsAndConditions(self, TermsAndConditions_id: int) -> "TermsAndConditions":
        TermsAndConditions = self.get_TermsAndConditions_by_id(TermsAndConditions_id)
        self._repo.toggle_active(TermsAndConditions)
        return TermsAndConditions

    def _auto_translate_all(self, TermsAndConditions) -> None:
        source = {"title": TermsAndConditions.title, "content": TermsAndConditions.content}
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            try:
                translated = self._translation.translate_batch(source, lang_name)
                self._repo.upsert_translation(
                    TermsAndConditions, lang_code,
                    translated.get("title", TermsAndConditions.title),
                    translated.get("content", TermsAndConditions.content),
                )
            except Exception:
                logger.exception("Failed to translate TermsAndConditions %s to %s", TermsAndConditions.pk, lang_code)
