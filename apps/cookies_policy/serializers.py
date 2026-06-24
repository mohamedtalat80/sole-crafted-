"""Serializers for the boats app."""
from datetime import datetime, timezone

from rest_framework import serializers
from apps.core.serializers import StrictModelSerializer, StrictSerializer
from apps.cookies_policy.models import CookiesPolicy


class CookiesPolicyWriteSerializer(StrictSerializer):
    """
    Input for POST /api/CookiesPolicy and PATCH /api/CookiesPolicy/{id}.
    """
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    display_order = serializers.IntegerField(min_value=1)
    

class CookiesPolicyReadSerializer(StrictModelSerializer):
    """Read representation of a registered CookiesPolicy."""
    title = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    def _language(self):
        request = self.context.get("request")
        if request and hasattr(request, "LANGUAGE_CODE"):
            return request.LANGUAGE_CODE
        return "en"

    def _get_field(self, obj, field):
        lang = self._language()
        if lang == "en":
            return getattr(obj, field)
        for t in obj.translations.all():
            if t.language == lang:
                return getattr(t, field)
        return getattr(obj, field) 
    def get_title(self, obj: CookiesPolicy) -> str:
        return self._get_field(obj, "title")

    def get_content(self, obj: CookiesPolicy) -> str:
        return self._get_field(obj, "content")

    class Meta:
        model = CookiesPolicy
        fields = [
            "id",
            "title",
            "content",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
class CookiesPolicyAdminReadSerializer(StrictModelSerializer):
    """Read representation of a registered CookiesPolicy."""

    class Meta:
        model = CookiesPolicy
        fields = [
            "id",
            "title",
            "content",
            "display_order",
            "updated_by",
            "created_at",
            "updated_at",
        ]
