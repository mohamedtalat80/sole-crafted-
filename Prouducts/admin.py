from django.contrib import admin

# Register your models here.
from .models import Product, Category, Tag, ProductImage, Rating
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(ProductImage)
admin.site.register(Rating)
