"""
FAQ model.
Every user type has his FAQ model inherting form the base FAQ 
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
class PrivacyPolicy(models.Model):
    title=models.CharField(max_length=255)
    content=models.TextField()
    display_order=models.PositiveIntegerField(default=0, db_index=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    updated_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    def __str__(self):
        return f"{self.title} "
class PrivacyPolicyTranslation(models.Model):
    SUPPORTED_LANGUAGES = [
        ("ar", _("Arabic")),
        ("nl", _("Dutch")),
        ("ru", _("Russian")),
        ("pt", _("Portuguese")),
        ("fr", _("French")),
        ("de", _("German")),
        ("hi", _("Hindi")),
        ("ko", _("Korean")),
        ("es", _("Spanish")),
    ]
    privacy_policy=models.ForeignKey(PrivacyPolicy,on_delete=models.CASCADE,related_name="translations")
    language=models.CharField(max_length=10,choices=SUPPORTED_LANGUAGES)
    title=models.CharField(_("Title"),max_length=255)
    content=models.TextField(_("Content"))
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.title} {self.language} "
    class Meta:
        unique_together = ("privacy_policy", "language")
    


    