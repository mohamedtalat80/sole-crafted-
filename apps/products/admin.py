from django.contrib import admin

from apps.products.models import (
    Category,
    CategoryTranslation,
    Colour,
    Product,
    ProductImage,
    ProductTranslation,
    Size,
    Tag,
    TagTranslation,
)





@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Colour)
class ColourAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
@admin.register(ProductTranslation)
class ProductTranslationAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "language"]
    search_fields = ["product__name", "language"]

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "brand", "price", "discount_percentage", "is_active", "category", "created_at"]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "brand"]
    filter_horizontal = ["tags", "sizes", "colors"]
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["id", "product"]
    search_fields = ["product__name"]
