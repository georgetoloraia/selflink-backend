from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.feed.composer import compose_for_you_feed, compose_following_feed


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
        items, next_cursor = compose_for_you_feed(
            request.user,
            cursor=cursor,
            limit=limit,
            serializer_context=self._serializer_context(request),
        )
        return Response({"items": items, "next": next_cursor})


class FollowingFeedView(BaseFeedView):
    def get(self, request: Request, *args, **kwargs) -> Response:  # type: ignore[override]
        limit, cursor = self._pagination_params(request)
        items, next_cursor = compose_following_feed(
            request.user,
            cursor=cursor,
            limit=limit,
            serializer_context=self._serializer_context(request),
        )
        return Response({"items": items, "next": next_cursor})
