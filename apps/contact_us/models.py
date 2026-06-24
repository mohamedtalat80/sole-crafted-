from functools import partial

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.core.utils.upload_utils import upload_to_uuid

class ContactMessage(models.Model):
    class SubjectType(models.TextChoices):
        GENERAL = "general", _("General")
        TRIP = "trip", _("Trip")
        RENT = "rent", _("Rent")
        SUPPORT = "support", _("Support")
        OTHER = "other", _("Other")

    full_name = models.CharField(verbose_name=_("full name"), max_length=70)
    email = models.EmailField(_("email"), max_length=254)

    subject = models.CharField(
        verbose_name=_("subject"),
        max_length=100,
        choices=SubjectType.choices
    )

    phone = models.CharField(
        verbose_name=_("phone"),
        max_length=254,
        null=True,
        blank=True
    )

    image = models.ImageField(
        verbose_name=_("image"),
        upload_to=partial(upload_to_uuid, folder_name="contact_messages"),
        null=True,
        blank=True
    )

    message = models.TextField(
        _("message"),
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name