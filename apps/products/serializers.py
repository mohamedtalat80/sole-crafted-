from __future__ import annotations

from rest_framework import serializers

from apps.core.fields import _ImageUploadField
from apps.core.serializers import MultipartJsonListMixin, StrictModelSerializer, StrictSerializer
from apps.core.utils.translation_utils import TRANSLATION_LANGUAGES
from apps.products.models import Category, Colour, Product, ProductImage, Size, Tag


class TranslatableSerializerMixin:
    """Resolves a translated field via Accept-Language, falling back to English."""

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
            if t.language == lang:
                val = getattr(t, field, None)
                return val if val is not None else getattr(obj, field)
        return getattr(obj, field)


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

class CategorySerializer(TranslatableSerializerMixin, StrictModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name"]

    def get_name(self, obj: Category):
        return self._get_field(obj, "name")


class CategoryWriteSerializer(StrictSerializer):
    name = serializers.CharField(max_length=100)
    is_active = serializers.BooleanField(default=True)


class CategoryAdminReadSerializer(StrictModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "is_active", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Tag
# ---------------------------------------------------------------------------

class TagSerializer(TranslatableSerializerMixin, StrictModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["id", "name"]

    def get_name(self, obj: Tag):
        return self._get_field(obj, "name")


class TagWriteSerializer(StrictSerializer):
    name = serializers.CharField(max_length=50)
    is_active = serializers.BooleanField(default=True)


class TagAdminReadSerializer(StrictModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "is_active", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------

class ColourSerializer(TranslatableSerializerMixin, StrictModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Colour
        fields = ["id", "name"]

    def get_name(self, obj: Colour):
        return self._get_field(obj, "name")


class ColourWriteSerializer(StrictSerializer):
    name = serializers.CharField(max_length=50)


class ColourAdminReadSerializer(StrictModelSerializer):
    class Meta:
        model = Colour
        fields = ["id", "name"]


# ---------------------------------------------------------------------------
# Size
# ---------------------------------------------------------------------------

class SizeSerializer(StrictModelSerializer):
    class Meta:
        model = Size
        fields = ["id", "name"]


class SizeWriteSerializer(StrictSerializer):
    name = serializers.CharField(max_length=50)


# ---------------------------------------------------------------------------
# ProductImage
# ---------------------------------------------------------------------------

class ProductImageSerializer(StrictModelSerializer):
    image = _ImageUploadField()

    class Meta:
        model = ProductImage
        fields = ["id", "image"]


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductReadSerializer(TranslatableSerializerMixin, StrictModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "description", "price", "brand",
            "discount_percentage", "sizes", "colors", "category",
            "tags", "images", "main_image",
        ]

    def get_name(self, obj: Product):
        return self._get_field(obj, "name")

    def get_description(self, obj: Product):
        return self._get_field(obj, "description")

    def get_sizes(self, obj: Product):
        return SizeSerializer(obj.sizes.all(), many=True, context=self.context).data

    def get_tags(self, obj: Product):
        return TagSerializer(obj.tags.all(), many=True, context=self.context).data

    def get_colors(self, obj: Product):
        return ColourSerializer(obj.colors.all(), many=True, context=self.context).data

    def get_category(self, obj: Product):
        return CategorySerializer(obj.category, context=self.context).data if obj.category else None

    def get_main_image(self, obj: Product):
        return obj.main_image.url if obj.main_image else None

    def get_images(self, obj: Product):
        return ProductImageSerializer(obj.images.all(), many=True, context=self.context).data


class ProductAdminReadSerializer(ProductReadSerializer):
    class Meta(ProductReadSerializer.Meta):
        fields = ProductReadSerializer.Meta.fields + ["is_active", "created_at", "updated_at"]


class ProductWriteSerializer(MultipartJsonListMixin, StrictSerializer):
    json_list_fields = ["sizes", "colors", "tags"]
    multipart_file_fields = ["images"]

    name = serializers.CharField(max_length=200)
    description = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100, required=False, default=0)
    is_active = serializers.BooleanField(required=False, default=True)
    main_image = serializers.ImageField(required=False)
    sizes = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    colors = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    category = serializers.IntegerField()
    tags = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    images = serializers.ListField(child=serializers.ImageField(), required=False, default=list)
    brand = serializers.CharField(max_length=100, required=False, default="")
