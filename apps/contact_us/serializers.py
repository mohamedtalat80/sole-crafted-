from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.core.serializers import StrictModelSerializer, MultipartJsonListMixin
from apps.contact_us.models import (
    ContactMessage
)
from apps.core.fields import _ImageUploadField
# -----------------------------
# Contact Message Serializer
# -----------------------------
class ContactMessageWriteSerializer(StrictModelSerializer):
    image = _ImageUploadField(required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    class Meta:
        model = ContactMessage
        fields = ['id', 'full_name', 'email', 'subject', 'phone', 'image', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']

class ContactMessageReadSerializer(StrictModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ContactMessage
        fields = ['id', 'full_name', 'email', 'subject', 'phone', 'image_url', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image_url(self, obj) -> str | None:
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None
