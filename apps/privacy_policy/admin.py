from django.contrib import admin
from apps.privacy_policy.models import PrivacyPolicy

@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display    = ["id", "title", "content", "updated_by", "created_at", "updated_at"]
    list_filter     = ["created_at"]
    search_fields   = ["title", "content"]
    readonly_fields = ["created_at", "updated_at"]
