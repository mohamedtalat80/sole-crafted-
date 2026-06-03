"""Serializers for the boats app."""
from datetime import datetime, timezone

from rest_framework import serializers
from apps.core.serializers import StrictModelSerializer, StrictSerializer
from apps.privacy_policy.models import PrivacyPolicy


class PrivacyPolicyWriteSerializer(StrictSerializer):
    """
    Input for POST /api/PrivacyPolicy and PATCH /api/PrivacyPolicy/{id}.
    """
    title = serializers.CharField(max_length=255)
    content = serializers.CharField()
    display_order = serializers.IntegerField(min_value=1)
    

class PrivacyPolicyReadSerializer(StrictModelSerializer):
    """Read representation of a registered PrivacyPolicy."""
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
    def get_title(self, obj: PrivacyPolicy) -> str:
        return self._get_field(obj, "title")

    def get_content(self, obj: PrivacyPolicy) -> str:
        return self._get_field(obj, "content")

    class Meta:
        model = PrivacyPolicy
        fields = [
            "id",
            "title",
            "content",
            "display_order",
            "is_active",
            
        ]
class PrivacyPolicyAdminReadSerializer(StrictModelSerializer):
    """Read representation of a registered PrivacyPolicy."""

    class Meta:
        model = PrivacyPolicy
        fields = [
            "id",
            "title",
            "content",
            "display_order",
            "updated_by",
            "created_at",
            "updated_at",
        ]
