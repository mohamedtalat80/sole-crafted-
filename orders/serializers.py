from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Payment
from Prouducts.models import Product
from user_profile.models import UserProfile
class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'address', 'state', 'city', 'country']
        read_only_fields = ['user']

class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'size', 'color', 'quantity', 'price']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_amount', 'created_at', 'updated_at']
        read_only_fields = ['user', 'total_amount', 'created_at', 'updated_at']

    def get_total_amount(self, obj):
        return sum([item.price * item.quantity for item in obj.items.all()])

class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'size', 'color', 'quantity', 'price_at_purchase']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'order_number', 'status', 'total_amount',
            'shipping_address', 'payment_status',
            'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['user', 'order_number', 'total_amount', 'created_at', 'updated_at', 'items']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
