from django.contrib import admin
from apps.cookies_policy.models import CookiesPolicy

@admin.register(CookiesPolicy)
class CookiesPolicyAdmin(admin.ModelAdmin):
    list_display    = ["id", "title", "content", "updated_by", "created_at", "updated_at"]
    list_filter     = ["created_at"]
    search_fields   = ["title", "content"]
    readonly_fields = ["created_at", "updated_at"]
