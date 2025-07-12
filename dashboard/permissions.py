from rest_framework import permissions
from .models import DashboardAdmin

class IsDashboardAdmin(permissions.BasePermission):
    """
    Custom permission to only allow dashboard admins.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            dashboard_admin = DashboardAdmin.objects.get(user=request.user)
            return dashboard_admin.is_dashboard_admin
        except DashboardAdmin.DoesNotExist:
            return False

class HasProductManagementPermission(permissions.BasePermission):
    """
    Permission to manage products.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            dashboard_admin = DashboardAdmin.objects.get(user=request.user)
            return dashboard_admin.is_dashboard_admin and dashboard_admin.dashboard_permissions.get('products', False)
        except DashboardAdmin.DoesNotExist:
            return False

class HasOrderManagementPermission(permissions.BasePermission):
    """
    Permission to manage orders.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            dashboard_admin = DashboardAdmin.objects.get(user=request.user)
            return dashboard_admin.is_dashboard_admin and dashboard_admin.dashboard_permissions.get('orders', False)
        except DashboardAdmin.DoesNotExist:
            return False

class HasPaymentViewPermission(permissions.BasePermission):
    """
    Permission to view payment analytics.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            dashboard_admin = DashboardAdmin.objects.get(user=request.user)
            return dashboard_admin.is_dashboard_admin and dashboard_admin.dashboard_permissions.get('payments', False)
        except DashboardAdmin.DoesNotExist:
            return False

class HasAnalyticsPermission(permissions.BasePermission):
    """
    Permission to view analytics.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        try:
            dashboard_admin = DashboardAdmin.objects.get(user=request.user)
            return dashboard_admin.is_dashboard_admin and dashboard_admin.dashboard_permissions.get('analytics', False)
        except DashboardAdmin.DoesNotExist:
            return False 