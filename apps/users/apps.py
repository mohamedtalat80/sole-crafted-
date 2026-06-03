from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "apps.users"
    label = "users"
    verbose_name = "Users"

    def ready(self):
        # Register post_save signal that auto-creates profiles
        import apps.users.signals  # noqa: F401
