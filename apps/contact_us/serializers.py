from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.core.serializers import StrictModelSerializer, MultipartJsonListMixin
from apps.contact_us.models import (
    ContactMessage, 
    ContactContent, 
    ContactInfo, 
    ContactIcon, 
    SocialMediaLink,
    ContactContentTranslation
)
from apps.core.utils.translation_utils import TRANSLATION_LANGUAGES
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
# -----------------------------
# Nested Serializers
# -----------------------------
class ContactIconSerializer(StrictModelSerializer):
    class Meta:
        model = ContactIcon
        fields = ['id', 'name', 'icon']


class SocialMediaLinkSerializer(StrictModelSerializer):
    url=serializers.URLField()
    class Meta:
        model = SocialMediaLink
        fields = ['id', 'url', 'type']
    
    def validate_url(self, value):
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value

class ContactInfoReadSerializer(StrictModelSerializer):
    icon = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactInfo
        fields = ['id', 'label', 'value', 'type', 'icon']
    def get_icon(self, obj):
        icon = obj.icons.first()
        if icon:
            return ContactIconSerializer(icon, context=self.context).data
        return None
      

class ContactInfoWriteSerializer(MultipartJsonListMixin, StrictModelSerializer):
    json_list_fields=('icon',)
    icon=serializers.ListField(
        child=ContactIconSerializer(),
        required=True
    )
    class Meta:
        model = ContactInfo
        fields = ['id', 'label', 'value', 'type', 'icon']
    


# -----------------------------
# Contact Content Serializers
# -----------------------------
class ContactContentReadSerializer(StrictModelSerializer):
    contact_infos = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    class Meta:
        model = ContactContent
        fields = ['id', 'title', 'description', 'contact_infos', 'social_links', 'updated_at']

    def _language(self) -> str:
        request = self.context.get("request")
        if request and hasattr(request, "LANGUAGE_CODE"):
            return request.LANGUAGE_CODE
        return self.context.get("language", "en")
    def _get_field(self, obj, field: str):
        lang = self._language()
        if lang == "en" or lang not in TRANSLATION_LANGUAGES:
            return getattr(obj, field)
        for t in obj.translations.all():
            if t.language_code == lang:
                val = getattr(t, field, None)
                return val if val is not None else getattr(obj, field)
        return getattr(obj, field)
    @extend_schema_field(ContactInfoReadSerializer(many=True))
    def get_contact_infos(self, obj):
        contact_infos = obj.contact_infos.all()
        serializer = ContactInfoReadSerializer(contact_infos, many=True, context=self.context)
        return serializer.data

    @extend_schema_field(SocialMediaLinkSerializer(many=True))
    def get_social_links(self, obj):
        social_links = obj.social_links.all()
        serializer = SocialMediaLinkSerializer(social_links, many=True, context=self.context)
        return serializer.data

    def get_title(self, obj) -> str:
        return self._get_field(obj, 'title')

    def get_description(self, obj) -> str:
        return self._get_field(obj, 'description')


class ContactContentWriteSerializer(MultipartJsonListMixin, StrictModelSerializer):
    contact_infos = serializers.ListField(
        child=ContactInfoWriteSerializer(),
        required=False
    )
    social_links = serializers.ListField(
        child=SocialMediaLinkSerializer(),
        required=False
    )
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False)

    json_list_fields = ('contact_infos', 'social_links')

    class Meta:
        model = ContactContent
        fields = ['id', 'title', 'description', 'contact_infos', 'social_links']
