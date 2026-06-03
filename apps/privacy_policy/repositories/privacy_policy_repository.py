from __future__ import annotations
from typing import Optional

from django.db import IntegrityError

from apps.core.exceptions import ConflictError, NotFoundError
from apps.privacy_policy.interfaces.privacy_policy_repository_interface import IPrivacyPolicyRepository
from apps.privacy_policy.models import PrivacyPolicy, PrivacyPolicyTranslation


class PrivacyPolicyRepository(IPrivacyPolicyRepository):

    def get_all(self):
        return PrivacyPolicy.objects.all().order_by("display_order")

    def get_all_active(self):
        return (
            PrivacyPolicy.objects.filter(is_active=True)
            .prefetch_related("translations")
            .order_by("display_order")
        )

    def get_by_id(self, policy_id: int) -> PrivacyPolicy:
        try:
            return PrivacyPolicy.objects.prefetch_related("translations").get(pk=policy_id)
        except PrivacyPolicy.DoesNotExist:
            raise NotFoundError(message="Privacy policy not found")

    def create(self, data: dict) -> PrivacyPolicy:
        try:
            return PrivacyPolicy.objects.create(
                title=data["title"],
                content=data["content"],
                display_order=data.get("display_order", 0),
            )
        except IntegrityError:
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": ["This display order is already in use. Please choose a different value."]},
            )

    def update(self, policy_id: int, data: dict, updated_by) -> PrivacyPolicy:
        instance = self.get_by_id(policy_id)
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

    def delete(self, instance: PrivacyPolicy) -> None:
        instance.delete()

    def toggle_active(self, instance: PrivacyPolicy) -> bool:
        instance.is_active = not instance.is_active
        instance.save()
        return instance.is_active

    def get_translation(self, instance: PrivacyPolicy, language: str) -> Optional[PrivacyPolicyTranslation]:
        try:
            return instance.translations.get(language=language)
        except PrivacyPolicyTranslation.DoesNotExist:
            return None

    def upsert_translation(
        self, instance: PrivacyPolicy, language: str, title: str, content: str
    ) -> PrivacyPolicyTranslation:
        obj, _ = PrivacyPolicyTranslation.objects.update_or_create(
            privacy_policy=instance,
            language=language,
            defaults={"title": title, "content": content},
        )
        return obj
