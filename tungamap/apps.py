from django.apps import AppConfig


class TungamapConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tungamap"
    verbose_name = "Tunga Map"

    def ready(self):
        from . import signals  # noqa: F401  (deletes photo files with their records)