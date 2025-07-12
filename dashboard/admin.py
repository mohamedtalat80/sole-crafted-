from django.contrib import admin
from .models import DashboardAdmin, AuditLog, DashboardConfiguration

@admin.register(DashboardAdmin)
class DashboardAdminAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_dashboard_admin', 'two_factor_enabled', 'last_dashboard_access', 'created_at']
    list_filter = ['is_dashboard_admin', 'two_factor_enabled', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'is_dashboard_admin')
        }),
        ('Security', {
            'fields': ('two_factor_enabled', 'dashboard_permissions')
        }),
        ('Timestamps', {
            'fields': ('last_dashboard_access', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'model_name', 'object_id', 'timestamp', 'ip_address']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__username', 'user__email', 'object_id', 'details']
    readonly_fields = ['id', 'timestamp', 'request_id']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Action Details', {
            'fields': ('action', 'model_name', 'object_id')
        }),
        ('User Information', {
            'fields': ('user', 'ip_address', 'user_agent')
        }),
        ('Additional Data', {
            'fields': ('details', 'request_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )

@admin.register(DashboardConfiguration)
class DashboardConfigurationAdmin(admin.ModelAdmin):
    list_display = ['key', 'description', 'updated_at', 'updated_by']
    search_fields = ['key', 'description']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('Configuration', {
            'fields': ('key', 'value', 'description')
        }),
        ('Metadata', {
            'fields': ('updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    ) 