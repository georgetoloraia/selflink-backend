from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

from django.conf import settings

try:  # pragma: no cover - optional dependency during local dev
    from opensearchpy import OpenSearch
except Exception:  # pragma: no cover - fall back when not installed
    OpenSearch = None  # type: ignore

USERS_INDEX = "users_v1"
POSTS_INDEX = "posts_v1"


@lru_cache(maxsize=1)
def get_client() -> Optional[OpenSearch]:
    if not getattr(settings, "OPENSEARCH_ENABLED", False):
        return None
    if OpenSearch is None:
        return None
    hosts = [
        {
            "host": getattr(settings, "OPENSEARCH_HOST", "localhost"),
            "port": getattr(settings, "OPENSEARCH_PORT", 9200),
            "scheme": getattr(settings, "OPENSEARCH_SCHEME", "http"),
        }
    ]
    auth = None
    user = getattr(settings, "OPENSEARCH_USER", None)
    password = getattr(settings, "OPENSEARCH_PASSWORD", None)
    if user and password:
        auth = (user, password)
    return OpenSearch(hosts=hosts, http_auth=auth, timeout=10, max_retries=2)  # type: ignore[arg-type]


def ensure_indices() -> None:
    client = get_client()
    if not client:
        return
    _ensure_index(client, USERS_INDEX, USER_INDEX_BODY)
    _ensure_index(client, POSTS_INDEX, POST_INDEX_BODY)


def _ensure_index(client: OpenSearch, name: str, body: Dict[str, Any]) -> None:
    if not client.indices.exists(name):  # type: ignore[attr-defined]
        client.indices.create(name, body=body)  # type: ignore[attr-defined]


USER_INDEX_BODY: Dict[str, Any] = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
    "mappings": {
        "properties": {
            "name": {"type": "text", "analyzer": "standard"},
            "handle": {"type": "keyword"},
            "bio": {"type": "text"},
            "locale": {"type": "keyword"},
        }
    },
}

POST_INDEX_BODY: Dict[str, Any] = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
    "mappings": {
        "properties": {
            "text": {"type": "text"},
            "author_id": {"type": "long"},
            "visibility": {"type": "keyword"},
            "created_at": {"type": "date"},
            "language": {"type": "keyword"},
        }
    },
}
