import uuid
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Avg, Q
from .models import AuditLog, DashboardAdmin
from orders.models import Order, Payment
from Prouducts.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()

def log_audit_action(user, action, model_name, object_id=None, details=None, request=None):
    """
    Log an audit action with request details.
    """
    audit_log = AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else None,
        details=details or {},
        ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR'),
        user_agent=getattr(request, 'META', {}).get('HTTP_USER_AGENT', ''),
        request_id=uuid.uuid4()
    )
    return audit_log

def update_dashboard_access(user):
    """
    Update the last dashboard access time for a user.
    """
    try:
        dashboard_admin = DashboardAdmin.objects.get(user=user)
        dashboard_admin.last_dashboard_access = timezone.now()
        dashboard_admin.save()
    except DashboardAdmin.DoesNotExist:
        pass

def calculate_sales_analytics(period='month'):
    """
    Calculate sales analytics for different periods.
    """
    now = timezone.now()
    
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=7)
    elif period == 'month':
        start_date = now - timedelta(days=30)
    elif period == 'year':
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=30)

    orders = Order.objects.filter(
        created_at__gte=start_date,
        status__in=['paid', 'delivered']
    )

    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    order_count = orders.count()
    avg_order_value = orders.aggregate(avg=Avg('total_amount'))['avg'] or 0

    return {
        'total_revenue': float(total_revenue),
        'order_count': order_count,
        'avg_order_value': float(avg_order_value),
        'period': period
    }

def calculate_order_statistics():
    """
    Calculate order status statistics.
    """
    stats = Order.objects.aggregate(
        pending=Count('id', filter=Q(status='pending')),
        processing=Count('id', filter=Q(status='processing')),
        paid=Count('id', filter=Q(status='paid')),
        shipped=Count('id', filter=Q(status='shipped')),
        delivered=Count('id', filter=Q(status='delivered')),
        cancelled=Count('id', filter=Q(status='cancelled'))
    )
    
    return stats

def calculate_product_statistics():
    """
    Calculate product statistics.
    """
    total_products = Product.objects.count()
    out_of_stock = Product.objects.filter(stock_quantity=0).count()
    low_stock = Product.objects.filter(stock_quantity__lte=5, stock_quantity__gt=0).count()
    
    return {
        'total': total_products,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        'in_stock': total_products - out_of_stock - low_stock
    }

def calculate_payment_statistics():
    """
    Calculate payment statistics.
    """
    total_payments = Payment.objects.count()
    successful_payments = Payment.objects.filter(status='SUCCESS').count()
    failed_payments = Payment.objects.filter(status='FAILED').count()
    pending_payments = Payment.objects.filter(status='PENDING').count()
    
    success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0
    
    return {
        'total': total_payments,
        'successful': successful_payments,
        'failed': failed_payments,
        'pending': pending_payments,
        'success_rate': round(success_rate, 2)
    }

def get_dashboard_overview():
    """
    Get comprehensive dashboard overview data.
    """
    # Sales analytics
    today_sales = calculate_sales_analytics('today')
    week_sales = calculate_sales_analytics('week')
    month_sales = calculate_sales_analytics('month')
    
    # Order statistics
    order_stats = calculate_order_statistics()
    
    # Product statistics
    product_stats = calculate_product_statistics()
    
    # Payment statistics
    payment_stats = calculate_payment_statistics()
    
    return {
        'sales': {
            'today': today_sales['total_revenue'],
            'this_week': week_sales['total_revenue'],
            'this_month': month_sales['total_revenue'],
            'growth_percentage': 15.5  # This would need historical data calculation
        },
        'orders': order_stats,
        'products': product_stats,
        'payments': payment_stats
    }

def generate_request_id():
    """
    Generate a unique request ID for tracking.
    """
    return str(uuid.uuid4())

def format_response_data(data, request_id=None, user=None):
    """
    Format API response with metadata.
    """
    return {
        'status': 'success',
        'data': data,
        'meta': {
            'timestamp': timezone.now().isoformat(),
            'request_id': request_id or generate_request_id(),
            'user': user.email if user else None
        }
    } 