"""
Management command: setup_periodic_tasks

Registers the Celery Beat periodic schedule for the users app in the database.
Run once after deployment (or after a DB wipe):

    python manage.py setup_periodic_tasks

This creates (or updates) the PeriodicTask entry so the Beat scheduler
knows to run purge_deactivated_accounts every day at 02:00 UTC.

The schedule can also be adjusted any time from the Django admin panel
under Periodic Tasks.
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = "Register Celery Beat periodic tasks in the database."

    def handle(self, *args, **options):
        # Daily at 02:00 UTC
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="2",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
        )

        task, created = PeriodicTask.objects.update_or_create(
            name="Purge deactivated user accounts (60-day rule)",
            defaults={
                "task": "users.purge_deactivated_accounts",
                "crontab": schedule,
                "enabled": True,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} periodic task: '{task.name}' "
                f"— runs daily at 02:00 UTC."
            )
        )
