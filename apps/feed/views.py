from __future__ import annotations

import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.feed.composer import compose_for_you_feed, compose_following_feed
from apps.feed.services.cache import FeedCache

logger = logging.getLogger(__name__)


class BaseFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def _pagination_params(self, request: Request) -> tuple[int, str | None]:
        default_limit = int(getattr(settings, "REST_FRAMEWORK", {}).get("PAGE_SIZE", 20))
        try:
            limit = int(request.query_params.get("limit", default_limit))
        except (TypeError, ValueError):
            limit = default_limit
        limit = max(1, min(limit, 100))
        cursor = request.query_params.get("cursor")
        return limit, cursor

    def _serializer_context(self, request: Request) -> dict:
        return {"request": request}


class ForYouFeedView(BaseFeedView):
    def get(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        limit, cursor = self._pagination_params(request)
        cache_hit = FeedCache.get(request.user.id, "for_you", cursor)
        if cache_hit is not None:
            logger.info("feed cache hit", extra={"user_id": request.user.id, "mode": "for_you", "cursor": cursor})
            return Response(cache_hit)

        start = time.monotonic()
        items, next_cursor = compose_for_you_feed(
            request.user,
            cursor=cursor,
            limit=limit,
            serializer_context=self._serializer_context(request),
        )
        elapsed = time.monotonic() - start
        payload = {"items": items, "next": next_cursor}
        FeedCache.set(request.user.id, "for_you", cursor, payload)
        logger.info(
            "feed cache miss composed",
            extra={"user_id": request.user.id, "mode": "for_you", "cursor": cursor, "elapsed_ms": int(elapsed * 1000)},
        )
        return Response(payload)


class FollowingFeedView(BaseFeedView):
    def get(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        limit, cursor = self._pagination_params(request)
        cache_hit = FeedCache.get(request.user.id, "following", cursor)
        if cache_hit is not None:
            logger.info("feed cache hit", extra={"user_id": request.user.id, "mode": "following", "cursor": cursor})
            return Response(cache_hit)

        start = time.monotonic()
        items, next_cursor = compose_following_feed(
            request.user,
            cursor=cursor,
            limit=limit,
            serializer_context=self._serializer_context(request),
        )
        elapsed = time.monotonic() - start
        payload = {"items": items, "next": next_cursor}
        FeedCache.set(request.user.id, "following", cursor, payload)
        logger.info(
            "feed cache miss composed",
            extra={
                "user_id": request.user.id,
                "mode": "following",
                "cursor": cursor,
                "elapsed_ms": int(elapsed * 1000),
            },
        )
        return Response(payload)


class FeedHealthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        cache_ok = False
        try:
            test_key = "feed_health_check"
            cache.set(test_key, "ok", 5)
            cache_ok = cache.get(test_key) == "ok"
        except Exception:
            cache_ok = False

        today = timezone.localdate().isoformat()
        insight_cache = {
            "mentor": cache.get(f"mentor_insight:{request.user.id}:{today}") is not None,
            "matrix": cache.get(f"matrix_insight:{request.user.id}:{today}") is not None,
            "soulmatch": cache.get(f"soulmatch_insight:{request.user.id}:{today}") is not None,
        }
        return Response(
            {
                "cache_connected": cache_ok,
                "insight_cache": insight_cache,
            }
        )
