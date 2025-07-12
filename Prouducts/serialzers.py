from rest_framework import serializers
from .models import Product,Favorite    
class HomeProductSerializer(serializers.ModelSerializer):
    class Meta:
        model=Product
        fields=[
            'id',
            'name',
            'brand',
            'price',    
            'discount_percentage',
            'is_available',
            'main_image',
            'description',
            'sizes',

        ]
class ProductDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model=Product
        fields=[
            'id',
            'name',
            'brand',
            'description',
            'price',    
            'discount_percentage',
            'is_available',
            'main_image',
            'sizes',
            'colors',
            'category',
            'stock_quantity'
        ]
class FavoriteSerializer(serializers.ModelSerializer):
    product=ProductDetailsSerializer(read_only=True)
    class Meta:
        model=Favorite
        fields=['id','product','created_at']
        read_only_fields=['user','created_at']
