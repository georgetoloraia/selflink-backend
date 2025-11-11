from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AnonymousUser
from django.db.models import BooleanField, Count, Exists, OuterRef, QuerySet, Value

from apps.social.models import Follow


def with_user_relationship_meta(queryset: QuerySet, user: Any | None) -> QuerySet:
    """
    Attach follower/following/post counts and follow state metadata to a user queryset.

    Keeping this logic centralized avoids duplicating annotations across views.
    """

    annotated = queryset.annotate(
        followers_count=Count("followers", distinct=True),
        following_count=Count("following", distinct=True),
        posts_count=Count("posts", distinct=True),
    )

    current_user = user
    if isinstance(current_user, AnonymousUser) or not getattr(current_user, "is_authenticated", False):
        return annotated.annotate(
            is_following=Value(False, output_field=BooleanField()),
        )

    return annotated.annotate(
        is_following=Exists(
            Follow.objects.filter(follower=current_user, followee=OuterRef("pk"))
        )
    )
