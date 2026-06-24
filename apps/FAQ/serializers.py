"""Serializers for the boats app."""
from datetime import datetime, timezone

from rest_framework import serializers
from apps.core.serializers import StrictModelSerializer, StrictSerializer
from apps.FAQ.models import FAQ


class FAQWriteSerializer(StrictSerializer):
    """
    Input for POST /api/FAQ and PATCH /api/FAQ/{id}.
    """
    question = serializers.CharField(max_length=255)
    answer = serializers.CharField(max_length=255)
    display_order = serializers.IntegerField(min_value=1)
    


class FAQReadSerializer(StrictModelSerializer):
    """Read representation of a registered FAQ."""
    question = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()

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
    def get_question(self, obj: FAQ) -> str:
        return self._get_field(obj, "question")

    def get_answer(self, obj: FAQ) -> str:
        return self._get_field(obj, "answer")

    class Meta:
        model = FAQ
        fields = [
            "id",
            "question",
            "answer",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]


class FAQToggleActiveSerializer(StrictModelSerializer):
    """Response for toggle active endpoint."""
    class Meta:
        model = FAQ
        fields = ["is_active"]
