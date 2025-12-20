from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.config.models import FeatureFlag

User = get_user_model()

GROUP_DEFINITIONS = {
    "moderation_team": {
        "description": "Moderation tools access",
        "permissions": [
            ("moderation", "report", ["view", "change", "add"]),
            ("moderation", "enforcement", ["view", "add", "change"]),
        ],
    },
    "config_admin": {
        "description": "Manage configuration and feature flags",
        "permissions": [
            ("config", "featureflag", ["view", "add", "change"]),
        ],
    },
    "support_staff": {
        "description": "Limited support access",
        "permissions": [
            ("users", "user", ["view"]),
            ("social", "post", ["view"]),
        ],
    },
}

DEFAULT_FLAGS = [
    ("mentor_voice_beta", "Enable mentor voice experience", False, 0.0),
    ("soulmatch_pro", "Unlock SoulMatch Pro features", False, 0.0),
]


class Command(BaseCommand):
    help = "Bootstrap admin user, groups, and feature flags"

    def add_arguments(self, parser):  # type: ignore[override]
        parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", "admin@selflink.app"))
        parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", "selflinkAdmin123"))
        parser.add_argument("--name", default=os.getenv("ADMIN_NAME", "SelfLink Admin"))

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]
        name = options["name"]

        admin_user = self._ensure_superuser(email=email, password=password, name=name)
        groups = self._ensure_groups()
        self._assign_admin_to_groups(admin_user, groups)
        self._ensure_feature_flags()

        self.stdout.write(self.style.SUCCESS("Admin bootstrap complete."))

    def _ensure_superuser(self, email: str, password: str, name: str):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "handle": email.split("@")[0],
                "name": name,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            self.stdout.write(f"Created superuser {email}")
        if not user.is_superuser:
            user.is_superuser = True
            user.is_staff = True
        user.set_password(password)
        user.save()
        return user

    def _ensure_groups(self) -> list[Group]:
        provisioned = []
        for name, config in GROUP_DEFINITIONS.items():
            group, _ = Group.objects.get_or_create(name=name)
            perms = []
            for app_label, model, actions in config["permissions"]:
                content_type = ContentType.objects.get(app_label=app_label, model=model)
                for action in actions:
                    codename = f"{action}_{model}"
                    permission = Permission.objects.get(content_type=content_type, codename=codename)
                    perms.append(permission)
            group.permissions.set(perms)
            provisioned.append(group)
        return provisioned

    def _assign_admin_to_groups(self, user: User, groups: list[Group]) -> None:
        for group in groups:
            user.groups.add(group)

    def _ensure_feature_flags(self) -> None:
        for key, description, enabled, rollout in DEFAULT_FLAGS:
            FeatureFlag.objects.update_or_create(
                key=key,
                defaults={
                    "description": description,
                    "enabled": enabled,
                    "rollout": rollout,
                },
            )
