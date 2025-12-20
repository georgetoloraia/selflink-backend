from .base import BASE_DIR, REST_FRAMEWORK
from .base import *  # noqa: F403

# Keep tests self-contained without external services.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_STORE_EAGER_RESULT = False
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

OPENSEARCH_ENABLED = False

MEDIA_ROOT = BASE_DIR / "tmp" / "test-media"

REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()
