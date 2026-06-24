from __future__ import annotations
from typing import List, TYPE_CHECKING

from apps.core.exceptions import ConflictError, NotFoundError
from apps.cookies_policy.interfaces.cookies_policy_repository_interface import ICookiesPolicyRepository
from apps.cookies_policy.models import CookiesPolicy
from apps.core.utils.translation_utils import TRANSLATION_LANGUAGES,TranslationService
import logging
from django.conf import settings
User=settings.AUTH_USER_MODEL
logger = logging.getLogger(__name__)
class CookiesPolicyService:

    def __init__(self, repository: ICookiesPolicyRepository, translation: TranslationService) -> None:
        self._repo = repository
        self._translation = translation
    def get_all_privacy_policies(self) -> List[CookiesPolicy]:
        return self._repo.get_all()

    def get_all_active_privacy_policies(self) -> List[CookiesPolicy]:
        return self._repo.get_all_active()

    def get_cookies_policy_by_id(self, cookies_policy_id: int) -> CookiesPolicy:
        cookies_policy = self._repo.get_by_id(cookies_policy_id)
        if cookies_policy is None:
            raise NotFoundError(message="CookiesPolicy not found")
        return cookies_policy

    def add_cookies_policy(self, data: dict) -> CookiesPolicy:
        display_order = data.get("display_order")
        if display_order is not None and CookiesPolicy.objects.filter(display_order=display_order).exists():
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": [f"Display order {display_order} is already used by another Cookies Policy."]},
            )
        instance = self._repo.create(data)
        self._auto_translate_all(instance)
        return instance

    def update_cookies_policy(self, cookies_policy_id: int, data: dict, updated_by: User) -> CookiesPolicy:
        display_order = data.get("display_order")
        if display_order is not None and CookiesPolicy.objects.filter(display_order=display_order).exclude(id=cookies_policy_id).exists():
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": [f"Display order {display_order} is already used by another Cookies Policy."]},
            )
        instance = self._repo.update(cookies_policy_id, data, updated_by)
        if "title" in data or "content" in data:
            self._auto_translate_all(instance)
        return instance

    def delete_cookies_policy(self, cookies_policy_id: int) -> None:
        cookies_policy = self.get_cookies_policy_by_id(cookies_policy_id)
        self._repo.delete(cookies_policy)

    def toggle_active_cookies_policy(self, cookies_policy_id: int) -> bool:
        cookies_policy = self.get_cookies_policy_by_id(cookies_policy_id)
        is_active = self._repo.toggle_active(cookies_policy)
        return is_active

    def _auto_translate_all(self, cookies_policy: CookiesPolicy) -> None:
        source = {"title": cookies_policy.title, "content": cookies_policy.content}
        for lang_code, lang_name in TRANSLATION_LANGUAGES.items():
            try:
                translated = self._translation.translate_batch(source, lang_name)
                self._repo.upsert_translation(
                    cookies_policy, lang_code,
                    translated.get("title", cookies_policy.title),
                    translated.get("content", cookies_policy.content),
                )
            except Exception:
                logger.exception("Failed to translate CookiesPolicy %s to %s", cookies_policy.pk, lang_code)
