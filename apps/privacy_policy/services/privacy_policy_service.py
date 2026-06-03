from __future__ import annotations

import logging

from apps.core.exceptions import ConflictError
from apps.privacy_policy.interfaces.privacy_policy_repository_interface import IPrivacyPolicyRepository
from apps.privacy_policy.models import PrivacyPolicy
from apps.core.utils.translation_utils import TRANSLATION_LANGUAGES, TranslationService

logger = logging.getLogger(__name__)


class PrivacyPolicyService:

    def __init__(self, repository: IPrivacyPolicyRepository, translation: TranslationService) -> None:
        self._repo = repository
        self._translation = translation

    def get_all_privacy_policies(self) -> list:
        return self._repo.get_all()

    def get_all_active_privacy_policies(self) -> list:
        return self._repo.get_all_active()

    def get_privacy_policy_by_id(self, policy_id: int) -> PrivacyPolicy:
        return self._repo.get_by_id(policy_id)

    def add_privacy_policy(self, data: dict) -> PrivacyPolicy:
        display_order = data.get("display_order")
        if display_order is not None and PrivacyPolicy.objects.filter(display_order=display_order).exists():
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": [f"Display order {display_order} is already used by another Privacy Policy."]},
            )
        instance = self._repo.create(data)
        self._auto_translate_all(instance)
        return instance

    def update_privacy_policy(self, policy_id: int, data: dict, updated_by) -> PrivacyPolicy:
        display_order = data.get("display_order")
        if display_order is not None and PrivacyPolicy.objects.filter(display_order=display_order).exclude(id=policy_id).exists():
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": [f"Display order {display_order} is already used by another Privacy Policy."]},
            )
        instance = self._repo.update(policy_id, data, updated_by)
        if "title" in data or "content" in data:
            self._auto_translate_all(instance)
        return instance

    def delete_privacy_policy(self, policy_id: int) -> None:
        instance = self._repo.get_by_id(policy_id)
        self._repo.delete(instance)

    def toggle_active_privacy_policy(self, policy_id: int) -> bool:
        instance = self._repo.get_by_id(policy_id)
        return self._repo.toggle_active(instance)

    def _auto_translate_all(self, instance: PrivacyPolicy) -> None:
        source = {"title": instance.title, "content": instance.content}
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            try:
                translated = self._translation.translate_batch(source, lang_name)
                self._repo.upsert_translation(
                    instance, lang_code,
                    translated.get("title", instance.title),
                    translated.get("content", instance.content),
                )
            except Exception:
                logger.exception("Failed to translate PrivacyPolicy %s to %s", instance.pk, lang_code)
