from django.contrib import admin
from apps.FAQ.models import FAQ

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display    = ["id", "question", "answer", "created_at"]
    search_fields   = ["question", "answer"]
    readonly_fields = ["created_at", "updated_at"]
