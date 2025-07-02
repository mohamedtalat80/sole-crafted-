from django.shortcuts import render
from rest_framework import generics, status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem, Order, OrderItem
from .serializers import CartSerializer, OrderSerializer
from Prouducts.models import Product
from django.db import transaction
from django.utils.crypto import get_random_string

# Create your views here.

class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_cart(self, user):
        cart, created = Cart.objects.get_or_create(user=user)
        return cart

    def get(self, request):
        cart = self.get_cart(request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def put(self, request):
        cart = self.get_cart(request.user)
        # Remove existing items
        cart.items.all().delete()
        items_data = request.data.get('items', [])
        for item in items_data:
            product = get_object_or_404(Product, pk=item['product'])
            CartItem.objects.create(
                cart=cart,
                product=product,
                size=item['size'],
                color=item['color'],
                quantity=item['quantity'],
                price=item.get('price', product.price)
            )
        cart.refresh_from_db()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def delete(self, request):
        cart = self.get_cart(request.user)
        cart.items.all().delete()
        cart.refresh_from_db()
        serializer = CartSerializer(cart)
        return Response(serializer.data)

class OrderViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all()
        if not cart_items:
            return Response({'detail': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)
        # Validate items (stock, price, etc.)
        total = 0
        for item in cart_items:
            product = item.product
            if not product.is_available:
                return Response({'detail': f'Product {product.name} is not available.'}, status=status.HTTP_400_BAD_REQUEST)
            # Optionally check stock here
            total += item.price * item.quantity
        # Create order
        order = Order.objects.create(
            user=request.user,
            order_number=get_random_string(12),
            status='pending',
            total_amount=total,
            shipping_address=request.data.get('shipping_address', ''),
            billing_address=request.data.get('billing_address', ''),
            payment_status=request.data.get('payment_status', 'pending'),
        )
        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                size=item.size,
                color=item.color,
                quantity=item.quantity,
                price_at_purchase=item.price
            )
        # Optionally clear cart
        cart.items.all().delete()
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
