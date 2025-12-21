from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.users.models import User


@pytest.mark.django_db
def test_audit_event_hash_chain_and_immutable():
    user = User.objects.create_user(email="audit@example.com", password="pass1234", handle="audit", name="Audit User")
    created_at = timezone.now()
    first = AuditEvent.objects.create(
        actor_user=user,
        action="rewards.seed",
        object_type="reward_event",
        object_id="seed-1",
        metadata={"points": 5},
        created_at=created_at - timedelta(seconds=2),
    )
    second = AuditEvent.objects.create(
        actor_user=user,
        action="rewards.seed",
        object_type="reward_event",
        object_id="seed-2",
        metadata={"points": 7},
        created_at=created_at - timedelta(seconds=1),
    )

    assert first.hash_self
    assert second.hash_prev == first.hash_self

    first.action = "rewards.update"
    with pytest.raises(ValidationError):
        first.save()
    with pytest.raises(ValidationError):
        first.delete()
