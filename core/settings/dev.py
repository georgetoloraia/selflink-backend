from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [  # type: ignore[index]
    "rest_framework.permissions.IsAuthenticatedOrReadOnly",
]
