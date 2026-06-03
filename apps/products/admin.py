from django.contrib import admin

from apps.products.models import Category, Product, ProductImage, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    search_fields = ["name"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "brand", "price", "discount_percentage", "is_available", "stock_quantity", "category"]
    list_filter = ["is_available", "category"]
    search_fields = ["name", "brand"]
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["id", "product"]
