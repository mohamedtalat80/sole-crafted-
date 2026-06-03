"""
Signals for the users app.

Auto-creates the appropriate profile (CustomerProfile or OwnerProfile)
whenever a new CustomUser is saved. This ensures every user always has
a matching profile record — regardless of whether they signed up via
the API, the admin panel, or a management command.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import CustomUser, CustomerProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a profile for newly created users based on their account_type.

    - customer → CustomerProfile
    - owner    → OwnerProfile

    Uses get_or_create to stay idempotent (safe if called more than once).
    Logs errors instead of raising — we don't want a profile creation
    failure to break the user creation transaction.
    """
    if not created:
        return

    try:
        if instance.account_type == CustomUser.AccountType.CUSTOMER:
            CustomerProfile.objects.get_or_create(user=instance)
    except Exception:
        logger.exception(
            "Failed to create profile for user %s (type=%s)",
            instance.pk,
            instance.account_type,
        )
