from django.urls import path
from .views import CartView, OrderListCreateAPIView, OrderDetailAPIView, PaymentCheckoutView, PaymentWebhookView, OrderStatusView

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('orders/', OrderListCreateAPIView.as_view(), name='order-list'),
    path('orders/<int:order_id>/', OrderDetailAPIView.as_view(), name='order-detail'),
    path('checkout/<int:order_id>/', PaymentCheckoutView.as_view(), name='payment-checkout'),
    path('webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('api/order-status/<int:order_id>/', OrderStatusView.as_view(), name='order_status'),
]