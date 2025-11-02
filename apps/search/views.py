from __future__ import annotations

from typing import List

from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.search.client import POSTS_INDEX, USERS_INDEX, get_client
from apps.social.models import Post
from apps.social.serializers import PostSerializer
from apps.users.models import User
from apps.users.serializers import UserSerializer


class BaseSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    index_name: str

    def get_query(self, request: Request) -> str:
        query = request.query_params.get("q", "").strip()
        if not query:
            raise Http404("Query required")
        return query

    def get_page_size(self, request: Request) -> int:
        try:
            return min(int(request.query_params.get("limit", 20)), 50)
        except (TypeError, ValueError):
            return 20


class UserSearchView(BaseSearchView):
    index_name = USERS_INDEX

    def get(self, request: Request) -> Response:
        query = self.get_query(request)
        limit = self.get_page_size(request)
        client = get_client()
        if client:
            response = client.search(
                index=self.index_name,
                body={
                    "size": limit,
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["name^2", "handle", "bio"],
                        }
                    },
                },
            )
            ids = [int(hit["_id"]) for hit in response["hits"]["hits"]]
            queryset = list(User.objects.filter(id__in=ids).select_related("settings"))
            # preserve order from OpenSearch
            user_map = {user.id: user for user in queryset}
            ordered = [user_map[user_id] for user_id in ids if user_id in user_map]
        else:
            ordered = list(
                User.objects.filter(
                    Q(name__icontains=query)
                    | Q(handle__icontains=query)
                    | Q(bio__icontains=query)
                )
                .select_related("settings")
                .order_by("-created_at")[:limit]
            )
        serializer = UserSerializer(ordered, many=True, context={"request": request})
        return Response(serializer.data)


class PostSearchView(BaseSearchView):
    index_name = POSTS_INDEX

    def get(self, request: Request) -> Response:
        query = self.get_query(request)
        limit = self.get_page_size(request)
        client = get_client()
        if client:
            response = client.search(
                index=self.index_name,
                body={
                    "size": limit,
                    "query": {
                        "match": {
                            "text": {
                                "query": query,
                                "operator": "and",
                            }
                        }
                    },
                    "sort": [
                        {"created_at": {"order": "desc"}}
                    ],
                },
            )
            ids = [int(hit["_id"]) for hit in response["hits"]["hits"]]
            posts = list(
                Post.objects.filter(id__in=ids)
                .select_related("author", "author__settings")
                .prefetch_related("media")
            )
            post_map = {post.id: post for post in posts}
            ordered = [post_map[post_id] for post_id in ids if post_id in post_map]
        else:
            ordered = list(
                Post.objects.filter(text__icontains=query)
                .select_related("author", "author__settings")
                .prefetch_related("media")
                .order_by("-created_at")[:limit]
            )
        serializer = PostSerializer(ordered, many=True, context={"request": request})
        return Response(serializer.data)
