from __future__ import annotations

from celery import shared_task

from apps.search import indexers
from apps.search.client import POSTS_INDEX, USERS_INDEX, ensure_indices, get_client
from apps.social.models import Post
from apps.users.models import User


def _index_document(index: str, document_id: int, body: dict) -> None:
    client = get_client()
    if not client:
        return
    ensure_indices()
    client.index(index=index, id=document_id, body=body)


def _delete_document(index: str, document_id: int) -> None:
    client = get_client()
    if not client:
        return
    try:
        client.delete(index=index, id=document_id)
    except Exception:  # pragma: no cover - ignore on missing doc
        pass


@shared_task
def index_user_task(user_id: int) -> None:
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        _delete_document(USERS_INDEX, user_id)
        return
    _index_document(USERS_INDEX, user_id, indexers.user_document(user))


@shared_task
def index_post_task(post_id: int) -> None:
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        _delete_document(POSTS_INDEX, post_id)
        return
    _index_document(POSTS_INDEX, post_id, indexers.post_document(post))


@shared_task
def delete_user_task(user_id: int) -> None:
    _delete_document(USERS_INDEX, user_id)


@shared_task
def delete_post_task(post_id: int) -> None:
    _delete_document(POSTS_INDEX, post_id)
