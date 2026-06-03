from django.contrib import admin
from apps.terms_and_conditions.models import TermsAndConditions

@admin.register(TermsAndConditions)
class TermsAndConditionsAdmin(admin.ModelAdmin):
    list_display    = ["id", "title", "content", "updated_by", "created_at", "updated_at"]
    list_filter     = ["created_at"]
    search_fields   = ["title", "content"]
    readonly_fields = ["created_at", "updated_at"]
