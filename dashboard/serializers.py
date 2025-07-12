from rest_framework import serializers
from .models import DashboardAdmin, AuditLog, DashboardConfiguration
from django.contrib.auth import get_user_model
from Prouducts.models import Product, Category
from orders.models import Order, OrderItem, Payment
from user_profile.models import UserProfile

User = get_user_model()

class DashboardAdminSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = DashboardAdmin
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_dashboard_admin', 'dashboard_permissions', 'last_dashboard_access',
            'two_factor_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['last_dashboard_access', 'created_at', 'updated_at']

class DashboardLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    two_factor_code = serializers.CharField(required=False, allow_blank=True)

class DashboardAuthVerifySerializer(serializers.Serializer):
    token = serializers.CharField()

class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'username', 'action', 'model_name', 'object_id',
            'details', 'ip_address', 'user_agent', 'timestamp', 'request_id'
        ]
        read_only_fields = ['id', 'timestamp', 'request_id']

class DashboardConfigurationSerializer(serializers.ModelSerializer):
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = DashboardConfiguration
        fields = ['key', 'value', 'description', 'updated_at', 'updated_by_username']
        read_only_fields = ['updated_at', 'updated_by_username']

# Product Management Serializers
class DashboardProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    sales_count = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'description', 'price', 'discount_percentage',
            'main_image', 'sizes', 'colors', 'category', 'category_name',
            'is_available', 'stock_quantity', 'sales_count', 'stock_status',
            'created_at', 'updated_at'
        ]

    def get_sales_count(self, obj):
        return OrderItem.objects.filter(product=obj).count()

    def get_stock_status(self, obj):
        if obj.stock_quantity == 0:
            return 'out_of_stock'
        elif obj.stock_quantity <= 5:
            return 'low_stock'
        else:
            return 'in_stock'

class DashboardProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name', 'brand', 'description', 'price', 'discount_percentage',
            'main_image', 'sizes', 'colors', 'category', 'is_available', 'stock_quantity'
        ]

# Order Management Serializers
class DashboardOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_brand = serializers.CharField(source='product.brand', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_brand', 'size', 'color',
            'quantity', 'price_at_purchase'
        ]

class DashboardOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.CharField(source='user.email', read_only=True)
    items_count = serializers.SerializerMethodField()
    items = DashboardOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'customer_name', 'customer_email', 'order_number',
            'status', 'total_amount', 'shipping_address', 'payment_status',
            'items_count', 'items', 'created_at', 'updated_at'
        ]

    def get_customer_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    def get_items_count(self, obj):
        return obj.items.count()

# Payment Analytics Serializers
class DashboardPaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_email = serializers.CharField(source='order.user.email', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'customer_email', 'payment_order_id',
            'paymob_payment_id', 'status', 'error_messages', 'created_at', 'updated_at'
        ] 