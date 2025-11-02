from __future__ import annotations

from typing import Tuple

from services.reco.config import settings
from services.reco.engine import rebuild_timeline

from apps.social.models import Follow
from apps.users.models import User


def rebuild_user_timeline(user_id: int) -> Tuple[int, int]:
    user = User.objects.get(id=user_id)
    follows = (
        Follow.objects.filter(follower=user)
        .select_related("followee")
        .order_by("-created_at")[: settings.max_follow_sources]
    )
    return rebuild_timeline(user, follows, limit=settings.default_limit)
