from __future__ import annotations

import logging
import os
from urllib.parse import urlparse
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def is_running_in_docker() -> bool:
    return os.getenv("RUNNING_IN_DOCKER", "").lower() == "true" or os.path.exists("/.dockerenv")


def validate_database_url_for_docker(database_url: str, in_docker: bool) -> None:
    if not in_docker or not database_url:
        return
    parsed = urlparse(database_url)
    host = parsed.hostname
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise ImproperlyConfigured(
            "DATABASE_URL points to localhost inside Docker. "
            "Use Docker hostnames like pgbouncer or postgres instead."
        )

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS: List[str] = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]

SITE_ID = 1

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "ratelimit",
    "django_prometheus",
    "storages",
    "channels",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "allauth.socialaccount.providers.github",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.social",
    "apps.messaging",
    "apps.mentor",
    "apps.astro",
    "apps.audit",
    "apps.profile",
    "apps.matching",
    "apps.matrix",
    "apps.payments",
    "apps.notifications",
    "apps.moderation",
    "apps.feed",
    "apps.media",
    "apps.config",
    "apps.reco",
    "apps.search",
    "apps.contrib_rewards",
    "apps.realtime",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DEFAULT_DATABASE_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
validate_database_url_for_docker(os.getenv("DATABASE_URL", ""), is_running_in_docker())
DATABASES: Dict[str, Dict[str, Any]] = {
    "default": dj_database_url.parse(
        os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        conn_max_age=600,
        ssl_require=os.getenv("DATABASE_SSL", "false").lower() == "true",
    )
}

REDIS_CACHE_URL = os.getenv("REDIS_URL", os.getenv("CACHE_URL", ""))
if REDIS_CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_CACHE_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "selflink-default",
        }
    }

RATELIMIT_USE_CACHE = "default"
RATE_LIMITS_ENABLED = os.getenv("RATE_LIMITS_ENABLED", "false").lower() == "true"
MENTOR_RPS_USER = int(os.getenv("MENTOR_RPS_USER", "2"))
MENTOR_RPS_GLOBAL = int(os.getenv("MENTOR_RPS_GLOBAL", "20"))
AUTH_RPS_IP = int(os.getenv("AUTH_RPS_IP", "5"))

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

REST_USE_JWT = True

ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ADAPTER = "apps.users.adapters.SelflinkSocialAccountAdapter"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "offline"},
    },
    "facebook": {
        "SCOPE": ["email", "public_profile"],
        "METHOD": "oauth2",
        "VERSION": "v18.0",
    },
    "github": {
        "SCOPE": ["user:email"],
    },
}

SOCIAL_AUTH_REDIRECT_URIS = {
    "google": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/social/google/callback/"),
    "facebook": os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8000/api/v1/auth/social/facebook/callback/"),
    "github": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/api/v1/auth/social/github/callback/"),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TZ", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").strip().lower()
_SUPPORTED_STORAGE_BACKENDS = {"local", "s3"}
if STORAGE_BACKEND not in _SUPPORTED_STORAGE_BACKENDS:
    raise ImproperlyConfigured(
        f"STORAGE_BACKEND must be one of {sorted(_SUPPORTED_STORAGE_BACKENDS)}; got {STORAGE_BACKEND!r}."
    )

logger = logging.getLogger(__name__)

if STORAGE_BACKEND == "local":
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

    _ignored_s3_vars = [
        name
        for name in ("S3_ENDPOINT", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY", "S3_BUCKET")
        if os.getenv(name)
    ]
    if _ignored_s3_vars:
        logger.warning(
            "STORAGE_BACKEND=local ignoring S3 settings: %s",
            ", ".join(sorted(_ignored_s3_vars)),
        )
else:
    try:
        import storages  # noqa: F401
    except ImportError as exc:
        raise ImproperlyConfigured("STORAGE_BACKEND=s3 requires django-storages.") from exc

    S3_ENDPOINT = os.getenv("S3_ENDPOINT", "").strip()
    S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID", "").strip()
    S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY", "").strip()
    S3_BUCKET = os.getenv("S3_BUCKET", "").strip()
    missing = [
        name
        for name, value in (
            ("S3_ENDPOINT", S3_ENDPOINT),
            ("S3_ACCESS_KEY_ID", S3_ACCESS_KEY_ID),
            ("S3_SECRET_ACCESS_KEY", S3_SECRET_ACCESS_KEY),
            ("S3_BUCKET", S3_BUCKET),
        )
        if not value
    ]
    if missing:
        raise ImproperlyConfigured(
            "STORAGE_BACKEND=s3 requires: " + ", ".join(missing)
        )

    AWS_S3_ENDPOINT_URL = S3_ENDPOINT
    AWS_ACCESS_KEY_ID = S3_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = S3_SECRET_ACCESS_KEY
    AWS_STORAGE_BUCKET_NAME = S3_BUCKET
    AWS_S3_ADDRESSING_STYLE = "path"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = os.getenv("S3_QUERYSTRING_AUTH", "true").lower() == "true"

    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}/"
    MEDIA_ROOT = None
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
SERVE_MEDIA = os.getenv("SERVE_MEDIA", "false").lower() == "true"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.CursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": (
        "apps.core.throttling.IPRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
        "apps.core.throttling.ScopedUserRateThrottle",
        "apps.core.throttling.ScopedIPRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "ip": os.getenv("THROTTLE_IP_RATE", "240/min"),
        "user": os.getenv("THROTTLE_USER_RATE", "120/min"),
        "anon": os.getenv("THROTTLE_ANON_RATE", "60/min"),
        "mentor": os.getenv("THROTTLE_MENTOR_RATE", "20/min"),
        "user:mentor": os.getenv("THROTTLE_MENTOR_RATE", "20/min"),
        "ip:mentor": os.getenv("THROTTLE_MENTOR_RATE", "20/min"),
        "astro": os.getenv("THROTTLE_ASTRO_RATE", "6/min"),
        "user:astro": os.getenv("THROTTLE_ASTRO_RATE", "6/min"),
        "ip:astro": os.getenv("THROTTLE_ASTRO_RATE", "6/min"),
        "matching": os.getenv("THROTTLE_MATCHING_RATE", "30/min"),
        "user:matching": os.getenv("THROTTLE_MATCHING_RATE", "30/min"),
        "ip:matching": os.getenv("THROTTLE_MATCHING_RATE", "30/min"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SelfLink API",
    "DESCRIPTION": "API documentation for the SelfLink platform",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.getenv("JWT_SIGNING_KEY", SECRET_KEY),
}

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8082",
    "http://127.0.0.1:8082",
]
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", ",".join(_DEFAULT_CORS_ORIGINS)).split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_BEAT_SCHEDULE = {
    "prune-old-timelines": {
        "task": "apps.feed.tasks.prune_old_timeline_entries",
        "schedule": int(os.getenv("FEED_PRUNE_INTERVAL_HOURS", "6")) * 3600,
        "args": (int(os.getenv("FEED_PRUNE_DAYS", "30")),),
    }
}

# --- Pub/Sub (realtime fanout) ---
# Prefer explicit PUBSUB_REDIS_URL; default to docker redis hostname to avoid localhost lookups
PUBSUB_REDIS_URL = os.getenv("PUBSUB_REDIS_URL", "redis://redis:6379/1")
REALTIME_CHANNELS_ENABLED = os.getenv("REALTIME_CHANNELS_ENABLED", "false").lower() == "true"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [PUBSUB_REDIS_URL]},
    }
}

# --- OpenSearch (align env names) ---
OPENSEARCH_ENABLED = os.getenv("OPENSEARCH_ENABLED", "true").lower() == "true"
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.getenv("OPENSEARCH_PORT", "9200"))
# accept both OPENSEARCH_USERNAME and OPENSEARCH_USER for safety
OPENSEARCH_USERNAME = os.getenv("OPENSEARCH_USERNAME", os.getenv("OPENSEARCH_USER", "admin"))
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")
OPENSEARCH_SCHEME = os.getenv("OPENSEARCH_SCHEME", "http")

SWISSEPH_DATA_PATH = os.getenv("SWISSEPH_DATA_PATH", str(BASE_DIR / "astro_data"))
ASTRO_RULES_VERSION = os.getenv("ASTRO_RULES_VERSION", "v1")
ASTRO_CACHE_TTL_SECONDS = int(os.getenv("ASTRO_CACHE_TTL_SECONDS", str(60 * 60 * 24 * 7)))
MATCH_RULES_VERSION = os.getenv("MATCH_RULES_VERSION", "v1")


FEATURE_FLAGS = {
    "mentor_llm": True,
    "ollama_support": True,
    "realtime": True,
    "soulmatch": os.getenv("FEATURE_SOULMATCH", "true").lower() == "true",
    "payments": os.getenv("FEATURE_PAYMENTS", "true").lower() == "true",
}

MODERATION_BANNED_WORDS = [
    word.strip()
    for word in os.getenv("MODERATION_BANNED_WORDS", "spam,scam,offensive").split(",")
    if word.strip()
]

LOGGING: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "strip_request_body": {
            "()": "apps.core.logging_filters.StripRequestBodyFilter",
        }
    },
    "formatters": {
        "console": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(levelname)s %(name)s %(message)s %(asctime)s %(request_id)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "filters": ["strip_request_body"],
        },
        "json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["strip_request_body"],
        },
    },
    "root": {
        "handlers": ["json"],
        "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "apps": {
            "handlers": ["json"],
            "level": os.getenv("APP_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["json"],
            "level": os.getenv("DJANGO_REQUEST_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
    },
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@selflink.app")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "false").lower() == "true"
