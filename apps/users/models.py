from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.core.models import BaseModel
from libs.idgen import generate_id


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: object) -> "User":
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> "User":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields: object) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.BigIntegerField(primary_key=True, default=generate_id, editable=False)
    email = models.EmailField(unique=True)
    handle = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    photo = models.URLField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    birth_time = models.TimeField(null=True, blank=True)
    birth_place = models.CharField(max_length=255, blank=True)
    locale = models.CharField(max_length=32, default="en-US")
    flags = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["handle", "name"]

    class Meta:
        indexes = [
            models.Index(fields=["handle"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.handle}<{self.email}>"


class UserSettings(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")
    privacy = models.CharField(max_length=32, default="public")
    dm_policy = models.CharField(max_length=32, default="everyone")
    language = models.CharField(max_length=32, default="en")
    quiet_hours = models.JSONField(default=dict, blank=True)
    push_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    digest_enabled = models.BooleanField(default=False)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"Settings<{self.user_id}>"


class Block(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocks")
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked_by")

    class Meta:
        unique_together = ("user", "target")


class Mute(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mutes")
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name="muted_by")

    class Meta:
        unique_together = ("user", "target")


class Device(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    push_token = models.CharField(max_length=255)
    device_type = models.CharField(max_length=32)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "push_token")
