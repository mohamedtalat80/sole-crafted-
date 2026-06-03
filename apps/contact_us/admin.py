from django.contrib import admin

from .models import ContactContent, ContactIcon, ContactInfo, ContactMessage, SocialMediaLink

class ContactIconInline(admin.StackedInline):
    model = ContactIcon
    extra = 1

class SocialMediaLinkInline(admin.StackedInline):
    model = SocialMediaLink
    extra = 1

class ContactInfoInline(admin.StackedInline):
    model = ContactInfo
    extra = 1
    inlines = [ContactIconInline]

@admin.register(ContactContent)
class ContactContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'description')
    inlines = [ContactInfoInline, SocialMediaLinkInline]

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
