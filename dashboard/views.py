from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import DashboardAdmin, AuditLog, DashboardConfiguration
from .serializers import (
    DashboardAdminSerializer, DashboardLoginSerializer, DashboardAuthVerifySerializer,
    AuditLogSerializer, DashboardProductSerializer, DashboardProductCreateSerializer,
    DashboardOrderSerializer, DashboardPaymentSerializer, DashboardConfigurationSerializer
)
from .permissions import (
    IsDashboardAdmin, HasProductManagementPermission, HasOrderManagementPermission,
    HasPaymentViewPermission, HasAnalyticsPermission
)
from .utils import (
    log_audit_action, update_dashboard_access, get_dashboard_overview,
    calculate_sales_analytics, calculate_order_statistics, calculate_product_statistics,
    calculate_payment_statistics, format_response_data
)
from Prouducts.models import Product, Category
from orders.models import Order, OrderItem, Payment
from user_profile.models import UserProfile
from django.contrib.auth import get_user_model

User = get_user_model()

# Authentication Views
class DashboardLoginView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = []

    @swagger_auto_schema(
        operation_description="Login to dashboard with admin credentials",
        request_body=DashboardLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'access_token': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh_token': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid credentials or 2FA required",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'requires_2fa': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            ),
            401: openapi.Response(description="Invalid credentials"),
            403: openapi.Response(description="User is not a dashboard admin")
        }
    )
    def post(self, request):
        serializer = DashboardLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            two_factor_code = serializer.validated_data.get('two_factor_code', '')

            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    try:
                        dashboard_admin = DashboardAdmin.objects.get(user=user)
                        if dashboard_admin.is_dashboard_admin:
                            # Check 2FA if enabled
                            if dashboard_admin.two_factor_enabled and not two_factor_code:
                                return Response({
                                    'status': 'error',
                                    'message': 'Two-factor authentication required',
                                    'requires_2fa': True
                                }, status=status.HTTP_400_BAD_REQUEST)

                            # Update last access
                            update_dashboard_access(user)
                            
                            # Generate tokens
                            refresh = RefreshToken.for_user(user)
                            access_token = refresh.access_token
                            
                            # Log login
                            log_audit_action(user, 'LOGIN', 'DashboardAdmin', user.id, {}, request)
                            
                            return Response({
                                'status': 'success',
                                'access_token': str(access_token),
                                'refresh_token': str(refresh),
                                'user': DashboardAdminSerializer(dashboard_admin).data
                            })
                        else:
                            return Response({
                                'status': 'error',
                                'message': 'User is not a dashboard admin'
                            }, status=status.HTTP_403_FORBIDDEN)
                    except DashboardAdmin.DoesNotExist:
                        return Response({
                            'status': 'error',
                            'message': 'User is not a dashboard admin'
                        }, status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response({
                        'status': 'error',
                        'message': 'Invalid credentials'
                    }, status=status.HTTP_401_UNAUTHORIZED)
            except User.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            'status': 'error',
            'message': 'Invalid data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class DashboardLogoutView(APIView):
    permission_classes = [IsDashboardAdmin]

    @swagger_auto_schema(
        operation_description="Logout from dashboard",
        responses={
            200: openapi.Response(
                description="Logout successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized")
        }
    )
    def post(self, request):
        log_audit_action(request.user, 'LOGOUT', 'DashboardAdmin', request.user.id, {}, request)
        return Response({
            'status': 'success',
            'message': 'Logged out successfully'
        })

class DashboardAuthVerifyView(APIView):
    permission_classes = [IsDashboardAdmin]

    @swagger_auto_schema(
        operation_description="Verify dashboard authentication",
        responses={
            200: openapi.Response(
                description="Authentication verified",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            403: openapi.Response(description="User is not a dashboard admin")
        }
    )
    def get(self, request):
        try:
            dashboard_admin = DashboardAdmin.objects.get(user=request.user)
            update_dashboard_access(request.user)
            return Response({
                'status': 'success',
                'user': DashboardAdminSerializer(dashboard_admin).data
            })
        except DashboardAdmin.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'User is not a dashboard admin'
            }, status=status.HTTP_403_FORBIDDEN)

# Analytics Overview
class DashboardOverviewView(APIView):
    permission_classes = [IsDashboardAdmin]

    @swagger_auto_schema(
        operation_description="Get dashboard overview analytics",
        responses={
            200: openapi.Response(
                description="Overview data retrieved",
                schema=openapi.Schema(type=openapi.TYPE_OBJECT)
            ),
            401: openapi.Response(description="Unauthorized")
        }
    )
    def get(self, request):
        overview_data = get_dashboard_overview()
        return Response(format_response_data(overview_data, user=request.user))

# Product Management Views
class DashboardProductListView(APIView):
    permission_classes = [HasProductManagementPermission]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="Get paginated list of products with filtering and search",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by status (available/unavailable)", type=openapi.TYPE_STRING),
            openapi.Parameter('category', openapi.IN_QUERY, description="Filter by category ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('stock', openapi.IN_QUERY, description="Filter by stock (out_of_stock/low_stock)", type=openapi.TYPE_STRING),
            openapi.Parameter('search', openapi.IN_QUERY, description="Search in name, brand, description", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description="Sort field", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_order', openapi.IN_QUERY, description="Sort order (asc/desc)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: DashboardProductSerializer(many=True),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied")
        }
    )
    def get(self, request):
        products = Product.objects.select_related('category').all()
        
        # Filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            if status_filter == 'available':
                products = products.filter(is_available=True)
            elif status_filter == 'unavailable':
                products = products.filter(is_available=False)
        
        category_filter = request.query_params.get('category')
        if category_filter:
            products = products.filter(category_id=category_filter)
        
        stock_filter = request.query_params.get('stock')
        if stock_filter:
            if stock_filter == 'out_of_stock':
                products = products.filter(stock_quantity=0)
            elif stock_filter == 'low_stock':
                products = products.filter(stock_quantity__lte=5, stock_quantity__gt=0)
        
        # Search
        search = request.query_params.get('search')
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(brand__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Sorting
        sort_by = request.query_params.get('sort_by', 'created_at')
        sort_order = request.query_params.get('sort_order', 'desc')
        
        if sort_order == 'desc':
            products = products.order_by(f'-{sort_by}')
        else:
            products = products.order_by(sort_by)
        
        # Pagination
        paginator = self.pagination_class()
        paginated_products = paginator.paginate_queryset(products, request)
        
        serializer = DashboardProductSerializer(paginated_products, many=True)
        
        log_audit_action(request.user, 'EXPORT', 'Product', None, {
            'filters': request.query_params.dict()
        }, request)
        
        return Response(format_response_data(serializer.data, user=request.user))

    @swagger_auto_schema(
        operation_description="Create a new product",
        request_body=DashboardProductCreateSerializer,
        responses={
            201: DashboardProductSerializer,
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied")
        }
    )
    def post(self, request):
        serializer = DashboardProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            log_audit_action(request.user, 'CREATE', 'Product', product.id, {
                'product_name': product.name
            }, request)
            
            return Response(
                format_response_data(DashboardProductSerializer(product).data, user=request.user),
                status=status.HTTP_201_CREATED
            )
        
        return Response({
            'status': 'error',
            'message': 'Invalid data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class DashboardProductDetailView(APIView):
    permission_classes = [HasProductManagementPermission]

    @swagger_auto_schema(
        operation_description="Get specific product details",
        responses={
            200: DashboardProductSerializer,
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Product not found")
        }
    )
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        serializer = DashboardProductSerializer(product)
        return Response(format_response_data(serializer.data, user=request.user))

    @swagger_auto_schema(
        operation_description="Update product information",
        request_body=DashboardProductCreateSerializer,
        responses={
            200: DashboardProductSerializer,
            400: openapi.Response(
                description="Validation error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Product not found")
        }
    )
    def put(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        serializer = DashboardProductCreateSerializer(product, data=request.data, partial=True)
        
        if serializer.is_valid():
            old_data = DashboardProductSerializer(product).data
            product = serializer.save()
            log_audit_action(request.user, 'UPDATE', 'Product', product.id, {
                'old_data': old_data,
                'new_data': DashboardProductSerializer(product).data
            }, request)
            
            return Response(format_response_data(DashboardProductSerializer(product).data, user=request.user))
        
        return Response({
            'status': 'error',
            'message': 'Invalid data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        operation_description="Delete a product",
        responses={
            200: openapi.Response(
                description="Product deleted successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="Cannot delete product with active orders",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Product not found")
        }
    )
    def delete(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        
        # Check for active orders
        active_orders = OrderItem.objects.filter(product=product).exists()
        if active_orders:
            return Response({
                'status': 'error',
                'message': 'Cannot delete product with active orders'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        product_name = product.name
        product.delete()
        
        log_audit_action(request.user, 'DELETE', 'Product', product_id, {
            'product_name': product_name
        }, request)
        
        return Response({
            'status': 'success',
            'message': 'Product deleted successfully'
        })

# Order Management Views
class DashboardOrderListView(APIView):
    permission_classes = [HasOrderManagementPermission]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="Get paginated list of orders with filtering and search",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by order status", type=openapi.TYPE_STRING),
            openapi.Parameter('payment_status', openapi.IN_QUERY, description="Filter by payment status", type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, description="Filter by start date", type=openapi.TYPE_STRING, format='date'),
            openapi.Parameter('date_to', openapi.IN_QUERY, description="Filter by end date", type=openapi.TYPE_STRING, format='date'),
            openapi.Parameter('customer', openapi.IN_QUERY, description="Search by customer email/name", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description="Sort field", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_order', openapi.IN_QUERY, description="Sort order (asc/desc)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: DashboardOrderSerializer(many=True),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied")
        }
    )
    def get(self, request):
        orders = Order.objects.select_related('user').prefetch_related('items').all()
        
        # Filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        payment_status_filter = request.query_params.get('payment_status')
        if payment_status_filter:
            orders = orders.filter(payment_status=payment_status_filter)
        
        date_from = request.query_params.get('date_from')
        if date_from:
            orders = orders.filter(created_at__gte=date_from)
        
        date_to = request.query_params.get('date_to')
        if date_to:
            orders = orders.filter(created_at__lte=date_to)
        
        # Search by customer
        customer_search = request.query_params.get('customer')
        if customer_search:
            orders = orders.filter(
                Q(user__email__icontains=customer_search) |
                Q(user__first_name__icontains=customer_search) |
                Q(user__last_name__icontains=customer_search)
            )
        
        # Sorting
        sort_by = request.query_params.get('sort_by', 'created_at')
        sort_order = request.query_params.get('sort_order', 'desc')
        
        if sort_order == 'desc':
            orders = orders.order_by(f'-{sort_by}')
        else:
            orders = orders.order_by(sort_by)
        
        # Pagination
        paginator = self.pagination_class()
        paginated_orders = paginator.paginate_queryset(orders, request)
        
        serializer = DashboardOrderSerializer(paginated_orders, many=True)
        
        log_audit_action(request.user, 'EXPORT', 'Order', None, {
            'filters': request.query_params.dict()
        }, request)
        
        return Response(format_response_data(serializer.data, user=request.user))

class DashboardOrderDetailView(APIView):
    permission_classes = [HasOrderManagementPermission]

    @swagger_auto_schema(
        operation_description="Get specific order details",
        responses={
            200: DashboardOrderSerializer,
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Order not found")
        }
    )
    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        serializer = DashboardOrderSerializer(order)
        return Response(format_response_data(serializer.data, user=request.user))

    @swagger_auto_schema(
        operation_description="Update order status and information",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, description="Order status"),
                'shipping_address': openapi.Schema(type=openapi.TYPE_STRING, description="Shipping address"),
                'payment_status': openapi.Schema(type=openapi.TYPE_STRING, description="Payment status")
            }
        ),
        responses={
            200: DashboardOrderSerializer,
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Order not found")
        }
    )
    def put(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        old_status = order.status
        
        # Update order fields
        if 'status' in request.data:
            order.status = request.data['status']
        
        if 'shipping_address' in request.data:
            order.shipping_address = request.data['shipping_address']
        
        if 'payment_status' in request.data:
            order.payment_status = request.data['payment_status']
        
        order.save()
        
        log_audit_action(request.user, 'STATUS_CHANGE', 'Order', order.id, {
            'old_status': old_status,
            'new_status': order.status
        }, request)
        
        return Response(format_response_data(DashboardOrderSerializer(order).data, user=request.user))

    @swagger_auto_schema(
        operation_description="Cancel an order and restore inventory",
        responses={
            200: openapi.Response(
                description="Order cancelled successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied"),
            404: openapi.Response(description="Order not found")
        }
    )
    def delete(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        
        # Restore product inventory
        for item in order.items.all():
            item.product.stock_quantity += item.quantity
            item.product.save()
        
        order.status = 'cancelled'
        order.save()
        
        log_audit_action(request.user, 'DELETE', 'Order', order.id, {
            'order_number': order.order_number,
            'reason': 'Admin cancellation'
        }, request)
        
        return Response({
            'status': 'success',
            'message': 'Order cancelled successfully'
        })

# Payment Analytics Views
class DashboardPaymentListView(APIView):
    permission_classes = [HasPaymentViewPermission]
    pagination_class = PageNumberPagination

    @swagger_auto_schema(
        operation_description="Get paginated list of payment transactions",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, description="Filter by payment status", type=openapi.TYPE_STRING),
            openapi.Parameter('date_from', openapi.IN_QUERY, description="Filter by start date", type=openapi.TYPE_STRING, format='date'),
            openapi.Parameter('date_to', openapi.IN_QUERY, description="Filter by end date", type=openapi.TYPE_STRING, format='date'),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description="Sort field", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_order', openapi.IN_QUERY, description="Sort order (asc/desc)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="Page number", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: DashboardPaymentSerializer(many=True),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied")
        }
    )
    def get(self, request):
        payments = Payment.objects.select_related('order__user').all()
        
        # Filtering
        status_filter = request.query_params.get('status')
        if status_filter:
            payments = payments.filter(status=status_filter)
        
        date_from = request.query_params.get('date_from')
        if date_from:
            payments = payments.filter(created_at__gte=date_from)
        
        date_to = request.query_params.get('date_to')
        if date_to:
            payments = payments.filter(created_at__lte=date_to)
        
        # Sorting
        sort_by = request.query_params.get('sort_by', 'created_at')
        sort_order = request.query_params.get('sort_order', 'desc')
        
        if sort_order == 'desc':
            payments = payments.order_by(f'-{sort_by}')
        else:
            payments = payments.order_by(sort_by)
        
        # Pagination
        paginator = self.pagination_class()
        paginated_payments = paginator.paginate_queryset(payments, request)
        
        serializer = DashboardPaymentSerializer(paginated_payments, many=True)
        
        return Response(format_response_data(serializer.data, user=request.user))

# Analytics Views
class DashboardAnalyticsView(APIView):
    permission_classes = [HasAnalyticsPermission]

    @swagger_auto_schema(
        operation_description="Get comprehensive analytics data",
        manual_parameters=[
            openapi.Parameter('period', openapi.IN_QUERY, description="Analytics period (month/week/day)", type=openapi.TYPE_STRING, default='month'),
        ],
        responses={
            200: openapi.Response(
                description="Analytics data retrieved",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'sales': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'orders': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'products': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'payments': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Permission denied")
        }
    )
    def get(self, request):
        period = request.query_params.get('period', 'month')
        
        sales_analytics = calculate_sales_analytics(period)
        order_stats = calculate_order_statistics()
        product_stats = calculate_product_statistics()
        payment_stats = calculate_payment_statistics()
        
        analytics_data = {
            'sales': sales_analytics,
            'orders': order_stats,
            'products': product_stats,
            'payments': payment_stats
        }
        
        return Response(format_response_data(analytics_data, user=request.user)) 