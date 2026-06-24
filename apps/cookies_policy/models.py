"""
Cookies Policy model.
Every user type has his Cookies Policy model inherting form the base Cookies Policy 
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
class CookiesPolicy(models.Model):
    title=models.CharField(max_length=255)
    content=models.TextField()
    display_order=models.PositiveIntegerField(default=0, db_index=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    updated_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    def __str__(self):
        return f"{self.title} "
class CookiesPolicyTranslation(models.Model):
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
    cookies_policy=models.ForeignKey(CookiesPolicy,on_delete=models.CASCADE,related_name="translations")
    language=models.CharField(max_length=10,choices=SUPPORTED_LANGUAGES)
    title=models.CharField(_("Title"),max_length=255)
    content=models.TextField(_("Content"))
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.title} {self.language} "
    class Meta:
        unique_together = ("cookies_policy", "language")
    


    