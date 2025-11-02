from __future__ import annotations

from typing import Dict

from django.utils import timezone

from apps.social.models import Post
from apps.users.models import User


def user_document(user: User) -> Dict[str, object]:
    return {
        "id": user.id,
        "name": user.name,
        "handle": user.handle,
        "bio": user.bio,
        "locale": user.locale,
        "created_at": user.created_at,
    }


def post_document(post: Post) -> Dict[str, object]:
    return {
        "id": post.id,
        "text": post.text,
        "author_id": post.author_id,
        "visibility": post.visibility,
        "language": post.language,
        "created_at": post.created_at or timezone.now(),
    }
