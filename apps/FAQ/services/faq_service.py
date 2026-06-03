from __future__ import annotations

from apps.core.exceptions import ConflictError, NotFoundError
from apps.FAQ.interfaces.faq_repository_interface import IFAQRepository
from apps.FAQ.models import FAQ
from apps.core.utils.translation_utils import TRANSLATION_LANGUAGES,TranslationService
import logging
logger = logging.getLogger(__name__)
class FAQService:

    def __init__(self, repository: IFAQRepository,translation:TranslationService) -> None:
        self._repo = repository
        self._translation = translation

    def get_FAQS_by_user_type(self, user_type: str) -> list:
        return self._repo.get_by_user_type(user_type)
        
    def get_all_active_FAQS_by_user_type(self, user_type: str) -> list:
        return self._repo.get_all_active_by_user_type(user_type)

    def get_FAQ_by_id(self, FAQ_id: int) -> "FAQ":
        faq = self._repo.get_by_id(FAQ_id)
        if faq is None:
            raise NotFoundError(message="FAQ not found")
        return faq

    def add_FAQ(self, user_type: str, data: dict) -> "FAQ":
        display_order = data.get("display_order")
        if display_order is not None and FAQ.objects.filter(user_type=user_type, display_order=display_order).exists():
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": [f"Display order {display_order} is already used by another {user_type} FAQ."]},
            )
        faq = self._repo.create(user_type, data)
        self._auto_translate_all(faq)
        return faq

    def update_FAQ(self, FAQ_id: int, data: dict) -> "FAQ":
        display_order = data.get("display_order")
        if display_order is not None:
            faq_instance = self.get_FAQ_by_id(FAQ_id)
            if FAQ.objects.filter(user_type=faq_instance.user_type, display_order=display_order).exclude(id=FAQ_id).exists():
                raise ConflictError(
                    message="Validation failed",
                    errors={"display_order": [f"Display order {display_order} is already used by another {faq_instance.user_type} FAQ."]},
                )
        faq =self._repo.update(FAQ_id, data)
        if "question" in data or "answer" in data:
            self._auto_translate_all(faq)
        return faq

    def delete_FAQ(self, FAQ_id: int) -> None:
        faq = self.get_FAQ_by_id(FAQ_id)
        self._repo.delete(faq)

    def toggle_active_FAQ(self, FAQ_id: int) -> "FAQ":
        faq = self.get_FAQ_by_id(FAQ_id)
        self._repo.toggle_active(faq)
        return faq

    def _auto_translate_all(self, faq) -> None:
        source = {"question": faq.question, "answer": faq.answer}
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            try:
                translated = self._translation.translate_batch(source, lang_name)
                self._repo.upsert_translation(
                    faq, lang_code,
                    translated.get("question", faq.question),
                    translated.get("answer", faq.answer),
                )
            except Exception:
                logger.exception("Failed to translate FAQ %s to %s", faq.pk, lang_code)
