from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers import StrictModelSerializer
from apps.products.models import Category, Product, ProductImage, Tag


class CategorySerializer(StrictModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class TagSerializer(StrictModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class ProductImageSerializer(StrictModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image"]


class ProductListSerializer(StrictModelSerializer):
    """Lightweight serializer for list/home view."""

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "brand",
            "price",
            "discount_percentage",
            "is_available",
            "main_image",
            "description",
            "sizes",
        ]


class ProductDetailSerializer(StrictModelSerializer):
    """Full serializer for product detail view."""

    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "brand",
            "description",
            "price",
            "discount_percentage",
            "is_available",
            "main_image",
            "sizes",
            "colors",
            "category",
            "tags",
            "images",
            "stock_quantity",
        ]


class ProductAdminReadSerializer(StrictModelSerializer):
    """Admin serializer — includes audit fields."""

    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "brand",
            "description",
            "price",
            "discount_percentage",
            "is_available",
            "main_image",
            "sizes",
            "colors",
            "category",
            "tags",
            "images",
            "stock_quantity",
            "created_at",
            "updated_at",
        ]
