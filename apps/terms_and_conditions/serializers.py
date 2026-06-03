"""Serializers for the boats app."""
from datetime import datetime, timezone

from rest_framework import serializers
from apps.core.serializers import StrictModelSerializer, StrictSerializer
from apps.terms_and_conditions.models import TermsAndConditions


class TermsAndConditionsWriteSerializer(StrictSerializer):
    """
    Input for POST /api/TermsAndConditions and PATCH /api/TermsAndConditions/{id}.
    """
    title = serializers.CharField(max_length=255)
    content = serializers.CharField(max_length=255)
    display_order = serializers.IntegerField(min_value=1)
    

class TermsAndConditionsReadSerializer(StrictModelSerializer):
    """Read representation of a registered TermsAndConditions."""
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
    def get_title(self, obj: TermsAndConditions) -> str:
        return self._get_field(obj, "title")

    def get_content(self, obj: TermsAndConditions) -> str:
        return self._get_field(obj, "content")

    class Meta:
        model = TermsAndConditions
        fields = [
            "id",
            "title",
            "content",
            "display_order",
            "is_active",
           
        ]
class TermsAndConditionsAdminReadSerializer(StrictModelSerializer):
    """Read representation of a registered TermsAndConditions."""

    class Meta:
        model = TermsAndConditions
        fields = [
            "id",
            "title",
            "content",
            "display_order",
            "updated_by",
            "created_at",
            "updated_at",
        ]
