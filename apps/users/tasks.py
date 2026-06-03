"""
Celery tasks for the users app.

Scheduled tasks:
  - purge_deactivated_accounts: runs daily, anonymises users whose
    60-day deactivation window has expired.

The periodic schedule is stored in the database via django-celery-beat
and can be managed from the Django admin panel.

To register the schedule on a fresh environment:
    python manage.py setup_periodic_tasks
    (or configure it in the admin under Periodic Tasks)
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="users.purge_deactivated_accounts",
    bind=True,
    max_retries=3,
    default_retry_delay=60 * 10,  # retry after 10 min on transient failure
)
def purge_deactivated_accounts(self):
    """
    Anonymise all user rows whose 60-day deactivation window has expired.

    Scheduled: daily (configured via django-celery-beat in the admin).

    Each user is anonymised in isolation — a failure on one row is logged
    and skipped so the rest of the batch is not affected.
    """
    from apps.users.repositories.user_repository import UserRepository

    repo = UserRepository()
    due = repo.get_users_due_for_purge()

    if not due:
        logger.info("purge_deactivated_accounts: no accounts due for purge.")
        return {"purged": 0}

    purged = 0
    for user in due:
        try:
            repo.anonymize_user(user)
            purged += 1
            logger.info("Purged deactivated account id=%s", user.pk)
        except Exception as exc:
            logger.exception("Failed to purge account id=%s: %s", user.pk, exc)

    logger.info("purge_deactivated_accounts: purged %d account(s).", purged)
    return {"purged": purged}
