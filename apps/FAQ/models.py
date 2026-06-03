"""
FAQ model.
Every user type has his FAQ model inherting form the base FAQ 
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
class FAQ(models.Model):
    class UserType(models.TextChoices):
        CUSTOMER="customer", _("Customer")
        OWNER="owner",_("Owner")
    question=models.TextField()
    answer=models.TextField()
    user_type=models.CharField(choices=UserType.choices,default=UserType.CUSTOMER)
    display_order=models.PositiveIntegerField(default=0, db_index=True)
    is_active=models.BooleanField(default=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.question} {self.user_type} "
class FAQTranslation(models.Model):
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
    faq=models.ForeignKey(FAQ,on_delete=models.CASCADE,related_name="translations")
    language=models.CharField(max_length=10,choices=SUPPORTED_LANGUAGES)
    question=models.TextField()
    answer=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"{self.question} {self.language} "
    class Meta:
        unique_together = ("faq", "language")
    


    