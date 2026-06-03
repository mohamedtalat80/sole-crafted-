"""
Management command: purge_deactivated_accounts

Anonymises user rows whose 60-day deactivation window has expired.

Run this daily via cron or a task scheduler:
    python manage.py purge_deactivated_accounts

Design:
- Delegates all ORM work to UserRepository (follows the service-layer pattern).
- Reports how many accounts were purged so the output can be logged.
- Idempotent — safe to run multiple times; already-anonymised rows are skipped.
"""
import logging

from django.core.management.base import BaseCommand

from apps.users.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Anonymise user accounts whose 60-day deactivation period has expired."

    def handle(self, *args, **options):
        repo = UserRepository()
        due = repo.get_users_due_for_purge()

        if not due:
            self.stdout.write("No accounts due for purge.")
            return

        purged = 0
        for user in due:
            try:
                repo.anonymize_user(user)
                purged += 1
                logger.info("Purged deactivated account id=%s", user.pk)
            except Exception:
                logger.exception("Failed to purge account id=%s", user.pk)

        self.stdout.write(
            self.style.SUCCESS(f"Purged {purged} deactivated account(s).")
        )
