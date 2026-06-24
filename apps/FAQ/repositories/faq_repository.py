"""ORM implementation of IFAQRepository."""
from __future__ import annotations
from typing import Optional

from django.db import IntegrityError

from apps.core.exceptions import ConflictError
from apps.FAQ.interfaces.faq_repository_interface import IFAQRepository
from apps.FAQ.models import FAQ,FAQTranslation

class FAQRepository(IFAQRepository):

    def get_all(self) -> Optional[FAQ]:
        return FAQ.objects.all().order_by("display_order")
    def get_all_active(self) -> Optional[FAQ]:
        return FAQ.objects.filter(is_active=True).prefetch_related("translations").order_by("display_order")

    def get_by_id(self, FAQ_id: int) -> Optional[FAQ]:
        try:
            return FAQ.objects.prefetch_related("translations").get(pk=FAQ_id)
        except FAQ.DoesNotExist:
            return None

    def create(self, data: dict) -> FAQ:
        try:
            return FAQ.objects.create(
                question=data["question"],
                answer=data["answer"],
                display_order=data.get("display_order", 0),
            )
        except IntegrityError:
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": ["This display order is already in use. Please choose a different value."]},
            )

    def update(self, FAQ_id: int, data: dict) -> FAQ:
        faq = self.get_by_id(FAQ_id)
        if faq is None:
            return None
        faq.question = data.get("question", faq.question)
        faq.answer = data.get("answer", faq.answer)
        if "display_order" in data:
            faq.display_order = data["display_order"]
        try:
            faq.save()
        except IntegrityError:
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": ["This display order is already in use. Please choose a different value."]},
            )
        return faq
    def delete(self, FAQ: FAQ) -> None:
        FAQ.delete()

    def toggle_active(self, FAQ: FAQ) -> None:
        FAQ.is_active = not FAQ.is_active
        FAQ.save()
        
    def get_translation(self, FAQ: FAQ, language: str) -> Optional[FAQTranslation]:
        try:
            return FAQ.translations.get(language=language)
        except FAQTranslation.DoesNotExist:
            return None
    def upsert_translation(self, FAQ: FAQ, language: str, question: str, answer: str) -> FAQTranslation:
        return FAQTranslation.objects.update_or_create(
            faq=FAQ,
            language=language,
            defaults={
                "question": question,
                "answer": answer,
            },
        )
