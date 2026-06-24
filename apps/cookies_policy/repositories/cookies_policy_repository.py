"""ORM implementation of ICookiesPolicyRepository."""
from __future__ import annotations
from typing import Optional

from django.db import IntegrityError
from django.db.models import QuerySet

from apps.core.exceptions import ConflictError
from apps.cookies_policy.interfaces.cookies_policy_repository_interface import ICookiesPolicyRepository
from apps.cookies_policy.models import CookiesPolicy,CookiesPolicyTranslation
from apps.core.exceptions import NotFoundError
from django.conf import settings
User=settings.AUTH_USER_MODEL
class CookiesPolicyRepository(ICookiesPolicyRepository):

    def get_all(self) -> QuerySet[CookiesPolicy]:
        return CookiesPolicy.objects.all().order_by("display_order")

    def get_all_active(self) -> QuerySet[CookiesPolicy]:
        return CookiesPolicy.objects.filter(is_active=True).prefetch_related("translations").order_by("display_order")

    def get_by_id(self, cookies_policy_id: int) -> Optional[CookiesPolicy]:
        try:
            return CookiesPolicy.objects.prefetch_related("translations").get(pk=cookies_policy_id)
        except CookiesPolicy.DoesNotExist:
            raise NotFoundError(message="Cookies policy not found")

    def create(self, data: dict) -> CookiesPolicy:
        try:
            return CookiesPolicy.objects.create(
                title=data["title"],
                content=data["content"],
                display_order=data.get("display_order", 0),
            )
        except IntegrityError:
            raise ConflictError(
                message="Validation failed",
                errors={"display_order": ["This display order is already in use. Please choose a different value."]},
            )

    def update(self, cookies_policy_id: int, data: dict, updated_by: User) -> CookiesPolicy:
        instance = self.get_by_id(cookies_policy_id)
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
    def delete(self, cookies_policy: CookiesPolicy) -> None:
        cookies_policy.delete()

    def toggle_active(self, cookies_policy: CookiesPolicy) -> bool:
        cookies_policy.is_active = not cookies_policy.is_active
        cookies_policy.save()
        return cookies_policy.is_active

    def get_translation(self, cookies_policy: CookiesPolicy, language: str) -> Optional[CookiesPolicyTranslation]:
        try:
            return cookies_policy.translations.get(language=language)
        except CookiesPolicyTranslation.DoesNotExist:
            return None
    def upsert_translation(self, cookies_policy: CookiesPolicy, language: str, title: str, content: str) -> CookiesPolicyTranslation:
        return CookiesPolicyTranslation.objects.update_or_create(
            cookies_policy=cookies_policy,
            language=language,
            defaults={
                "title": title,
                "content": content,
            },
        )
