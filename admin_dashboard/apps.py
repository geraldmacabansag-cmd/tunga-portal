from django.apps import AppConfig


class AdminDashboardConfig(AppConfig):
    name = 'admin_dashboard'

    def ready(self):
        from . import signals  # noqa: F401  (Super Admin bell notifications)