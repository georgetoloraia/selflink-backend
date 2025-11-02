from django.apps import AppConfig


class SocialConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.social"
    verbose_name = "Social"

    def ready(self) -> None:
        try:
            import apps.social.signals  # noqa: F401
        except ImportError:
            pass
