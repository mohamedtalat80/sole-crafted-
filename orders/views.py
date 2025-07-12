from django.shortcuts import render
from rest_framework import generics, status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem, Order, OrderItem, Payment
from .serializers import CartSerializer, OrderSerializer, PaymentSerializer, UserInfoSerializer
from Prouducts.models import Product
from django.db import transaction
from django.utils.crypto import get_random_string
from django.views.generic import View
from django.http import HttpResponse
from user_profile.models import UserProfile
from .services import PaymobService
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import uuid
import logging
from django.conf import settings
from decouple import config

logger = logging.getLogger(__name__)

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

class OrderListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all()
        user_info = get_object_or_404(UserProfile, user=request.user)
        if not cart_items:
            return Response({'detail': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)
        total = 0
        for item in cart_items:
            product = item.product
            if not product.is_available:
                return Response({'detail': f'Product {product.name} is not available.'}, status=status.HTTP_400_BAD_REQUEST)
            total += item.price * item.quantity
        order = Order.objects.create(
            user=request.user,
            order_number=get_random_string(12),
            status='pending',
            total_amount=total,
            shipping_address=user_info.address,
            payment_status=request.data.get('payment_status', 'pending'),
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                size=item.size,
                color=item.color,
                quantity=item.quantity,
                price_at_purchase=item.price
            )
        cart.items.all().delete()
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class OrderDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, user=request.user)
        serializer = OrderSerializer(order)
        return Response(serializer.data)


    
class PaymentCheckoutView(APIView):
    """
    Initiates a Paymob payment for an order and returns the payment iframe URL.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        user_info=UserProfile.objects.get(user=request.user)
        try:
            # 1. Get Paymob auth token
            token = PaymobService.get_auth_token()
            # 2. Prepare items for Paymob
            items = []
            for item in order.items.all():
                items.append({
                    "name": str(item.product),
                    "amount_cents": int(item.price_at_purchase * 100),
                    "description": f" {item.product.name} {item.size} {item.color}",
                    "quantity": item.quantity,
                })
            # 3. Create Paymob order
            order_resp = PaymobService.create_order(
                token=token,
                currency="EGP",
                amount_cents=int(order.total_amount * 100),
                items=items,
                delivery=False
            )
            paymob_order_id = order_resp["id"]
            # 4. Prepare billing data
            billing_data = {
                "email": getattr(order.user, 'email', 'user@example.com'),
                "first_name": getattr(order.user, 'first_name', 'John'),
                "last_name": getattr(order.user, 'last_name', 'Doe'),
                "phone_number": getattr(order.user, 'phone', '+201234567890'),
                "apartment": "NA",
                "floor": "NA",
                "street": getattr(user_info, 'street', 'NA'),
                "building": "NA",
                "city": getattr(user_info, 'city', 'NA'),
                "country": getattr(user_info, 'country', 'NA'),
            }
            # 5. Generate payment key
            payment_key = PaymobService.generate_payment_key(
                token=token,
                currency="EGP",
                expiration=3600,
                amount_cents=int(order.total_amount * 100),
                order_id=paymob_order_id,
                billing_data=billing_data
            )
            # 6. Save Payment record
            payment = Payment.objects.create(
                order=order,
                payment_order_id=str(uuid.uuid4()),
                paymob_payment_id=paymob_order_id,
                status="PENDING",
                error_messages=""
            )
            # 7. Return payment URL
            iframe_url = PaymobService.get_payment_url(
                payment_key=payment_key,
                iframe_id=config('IFRAME_ID')
            )
            return Response({"iframe_url": iframe_url, "payment_id": payment.id}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Payment initiation failed: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(APIView):
    """
    Handles Paymob payment response webhooks.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = request.data if hasattr(request, 'data') else request.POST
            
            # Validate required data
            if not data:
                return Response({"detail": "No data provided"}, status=status.HTTP_400_BAD_REQUEST)
            
            paymob_order_id = data.get('order', {}).get('id') or data.get('order_id')
            if not paymob_order_id:
                return Response({"detail": "Missing order_id"}, status=status.HTTP_400_BAD_REQUEST)
                
            success = str(data.get('success', '')).lower() == 'true' or data.get('txn_response_code') == 'APPROVED'
            error_msg = data.get('error_occured') or data.get('message') or ''
            
            # Optionally: verify HMAC here
            payment = Payment.objects.filter(paymob_payment_id=paymob_order_id).first()
            if payment:
                payment.status = "SUCCESS" if success else "FAILED"
                payment.error_messages = error_msg
                payment.save()
                # Update order status
                if success:
                    payment.order.status = 'paid'
                    payment.order.payment_status = 'paid'
                else:
                    payment.order.status = 'pending'
                    payment.order.payment_status = 'pending'
                payment.order.save()
            logger.info(f"Webhook received for Paymob order {paymob_order_id}: success={success}")
            return Response({"status": "ok"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class OrderStatusView(APIView):
    def get(self, request, order_id):
        order = Order.objects.get(id=order_id)
        return Response({'status': order.payment_status})
