"""ORM implementation of ITermsAndConditionsRepository."""
from __future__ import annotations
from typing import Optional

from django.db import IntegrityError

from apps.core.exceptions import ConflictError
from apps.terms_and_conditions.interfaces.terms_and_conditions_repository_interface import ITermsAndConditionsRepository
from apps.terms_and_conditions.models import TermsAndConditions,TermsAndConditionsTranslation
from django.conf import settings
User=settings.AUTH_USER_MODEL
class TermsAndConditionsRepository(ITermsAndConditionsRepository):

    def get_all(self) -> Optional[TermsAndConditions]:
        return TermsAndConditions.objects.all().order_by("display_order")

    def get_all_active(self) -> Optional[TermsAndConditions]:
        return TermsAndConditions.objects.filter(is_active=True).prefetch_related("translations").order_by("display_order")

    def get_by_id(self, TermsAndConditions_id: int) -> Optional[TermsAndConditions]:
        try:
            return TermsAndConditions.objects.prefetch_related("translations").get(pk=TermsAndConditions_id)
        except TermsAndConditions.DoesNotExist:
            return None

    def create(self, data: dict) -> TermsAndConditions:
        try:
            return TermsAndConditions.objects.create(
                title=data["title"],
                content=data["content"],
                display_order=data.get("display_order", 0),
            )
        except IntegrityError:
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": ["This display order is already in use. Please choose a different value."]},
            )

    def update(self, TermsAndConditions_id: int, data: dict, updated_by: User) -> TermsAndConditions:
        instance = self.get_by_id(TermsAndConditions_id)
        if instance is None:
            return None
        instance.title = data.get("title", instance.title)
        instance.content = data.get("content", instance.content)
        if "display_order" in data:
            instance.display_order = data["display_order"]
        instance.updated_by = updated_by
        try:
            instance.save()
        except IntegrityError:
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": ["This display order is already in use. Please choose a different value."]},
            )
        return instance
    def delete(self, TermsAndConditions: TermsAndConditions) -> None:
        TermsAndConditions.delete()

    def toggle_active(self, TermsAndConditions: TermsAndConditions) -> None:
        TermsAndConditions.is_active = not TermsAndConditions.is_active
        TermsAndConditions.save()

    def get_translation(self, TermsAndConditions: TermsAndConditions, language: str) -> Optional[TermsAndConditionsTranslation]:
        try:
            return TermsAndConditions.translations.get(language=language)
        except TermsAndConditionsTranslation.DoesNotExist:
            return None
    def upsert_translation(self, TermsAndConditions: TermsAndConditions, language: str, title: str, content: str) -> TermsAndConditionsTranslation:
        return TermsAndConditionsTranslation.objects.update_or_create(
            terms_and_conditions=TermsAndConditions,
            language=language,
            defaults={
                "title": title,
                "content": content,
            },
        )
