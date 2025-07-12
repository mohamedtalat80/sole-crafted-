from django.urls import path
from .views import (
    DashboardLoginView, DashboardLogoutView, DashboardAuthVerifyView,
    DashboardOverviewView, DashboardProductListView, DashboardProductDetailView,
    DashboardOrderListView, DashboardOrderDetailView, DashboardPaymentListView,
    DashboardAnalyticsView
)

app_name = 'dashboard'

urlpatterns = [
    # Authentication
    path('auth/login/', DashboardLoginView.as_view(), name='dashboard-login'),
    path('auth/logout/', DashboardLogoutView.as_view(), name='dashboard-logout'),
    path('auth/verify/', DashboardAuthVerifyView.as_view(), name='dashboard-verify'),
    
    # Overview
    path('analytics/overview/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    
    # Products Management
    path('products/', DashboardProductListView.as_view(), name='dashboard-products'),
    path('products/<int:product_id>/', DashboardProductDetailView.as_view(), name='dashboard-product-detail'),
    
    # Orders Management
    path('orders/', DashboardOrderListView.as_view(), name='dashboard-orders'),
    path('orders/<int:order_id>/', DashboardOrderDetailView.as_view(), name='dashboard-order-detail'),
    
    # Payments Analytics
    path('payments/transactions/', DashboardPaymentListView.as_view(), name='dashboard-payments'),
    
    # Analytics
    path('analytics/', DashboardAnalyticsView.as_view(), name='dashboard-analytics'),
] 