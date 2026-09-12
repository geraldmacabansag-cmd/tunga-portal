from django.apps import AppConfig


class OfficeDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'office_dashboard'

    def ready(self):
        import office_dashboard.signals