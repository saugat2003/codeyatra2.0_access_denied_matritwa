from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "main"
    verbose_name = "Main Application"

    def ready(self):
        """Import signal handlers when the app is ready."""
        import main.signals  # noqa: F401
