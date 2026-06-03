from functools import partial

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.core.utils.upload_utils import upload_to_uuid


# Kept for historical migrations that still reference these callables.
def contact_message_image_path(instance, filename):
    return upload_to_uuid(instance, filename, folder_name="contact_messages")


def contact_icon_image_path(instance, filename):
    name=instance.name.lower().replace(" ", "_")
    return f'contact_icons/{name}/{filename}'


# -----------------------------
# Contact Content (Main Container)
# -----------------------------
class ContactContent(models.Model):
    title = models.CharField(verbose_name=_("title"), max_length=255)
    description = models.TextField(verbose_name=_("description"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    def clean(self, *args, **kwargs):
        if not self.pk and ContactContent.objects.exists():
            raise ValidationError(_("Only one ContactContent instance is allowed."))
        super().clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

# -----------------------------
# Contact Icon
# -----------------------------
class ContactIcon(models.Model):
    contact_info = models.ForeignKey(
        "ContactInfo",
        verbose_name=_("contact info"),
        on_delete=models.CASCADE,
        related_name="icons"
    )

    name = models.CharField(verbose_name=_("name"), max_length=255)
    icon = models.ImageField(verbose_name=_("icon"), upload_to=partial(upload_to_uuid, folder_name="contact_icons"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# -----------------------------
# Contact Info 
# -----------------------------
class ContactInfo(models.Model):
    class ContactInfoType(models.TextChoices):
        ADDRESS = "address", _("Address")
        PHONE = "phone", _("Phone")
        EMAIL = "email", _("Email")
        WHATSAPP = "whatsapp", _("WhatsApp")

    contact = models.ForeignKey(
        ContactContent,
        verbose_name=_("contact content"),
        on_delete=models.CASCADE,
        related_name="contact_infos"
    )

    label = models.CharField(verbose_name=_("label"), max_length=255)
    value = models.CharField(verbose_name=_("value"), max_length=255)

    type = models.CharField(
        verbose_name=_("type"),
        max_length=50,
        choices=ContactInfoType.choices
    )

 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['type'], name='unique_contact_info_type_per_contact')
        ]
    def __str__(self):
        return f"{self.label}: {self.value}"


# -----------------------------
# Social Media Links
# -----------------------------
class SocialMediaLink(models.Model):
    class SocialMediaType(models.TextChoices):
        FACEBOOK = "facebook", _("Facebook")
        TWITTER = "twitter", _("Twitter")
        INSTAGRAM = "instagram", _("Instagram")
        LINKEDIN = "linkedin", _("LinkedIn")
        YOUTUBE = "youtube", _("YouTube")
        OTHER = "other", _("Other")

    contact = models.ForeignKey(
        ContactContent,
        verbose_name=_("contact content"),
        on_delete=models.CASCADE,
        related_name="social_links"
    )

    url = models.URLField(verbose_name=_("url"), max_length=255)

    type = models.CharField(
        verbose_name=_("type"),
        max_length=50,
        choices=SocialMediaType.choices
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type}: {self.url}"

# -----------------------------
# Contact Content translation 
# -----------------------------
class ContactContentTranslation(models.Model):
    contact_content = models.ForeignKey(
        ContactContent,
        verbose_name=_("contact content"),
        on_delete=models.CASCADE,
        related_name="translations"
    )

    language_code = models.CharField(verbose_name=_("language code"), max_length=10)
    title = models.CharField(verbose_name=_("title"), max_length=255)
    description = models.TextField(verbose_name=_("description"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('contact_content', 'language_code')

    def __str__(self):
        return f"{self.contact_content.title} ({self.language_code})"

# -----------------------------
# Contact Message 
# -----------------------------
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