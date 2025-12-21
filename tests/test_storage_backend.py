from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.test import override_settings

from apps.messaging.models import Message, MessageAttachment, Thread


@pytest.mark.django_db
def test_local_storage_url_uses_media_prefix():
    user = get_user_model().objects.create_user(
        email="media-local@example.com",
        password="pass12345",
        handle="media_local",
        name="Media Local",
    )
    thread = Thread.objects.create(created_by=user)
    message = Message.objects.create(
        thread=thread,
        sender=user,
        type=Message.Type.IMAGE,
    )
    attachment = MessageAttachment.objects.create(
        message=message,
        file="messages/attachments/test.png",
        type=MessageAttachment.AttachmentType.IMAGE,
        mime_type="image/png",
    )

    assert settings.STORAGE_BACKEND == "local"
    assert settings.STORAGES["default"]["BACKEND"].endswith("FileSystemStorage")
    assert attachment.file.url.startswith("/media/")


@pytest.mark.django_db
def test_s3_storage_url_is_absolute():
    pytest.importorskip("storages.backends.s3boto3")
    s3_settings = {
        "STORAGE_BACKEND": "s3",
        "AWS_S3_ENDPOINT_URL": "http://minio:9000",
        "AWS_ACCESS_KEY_ID": "minio",
        "AWS_SECRET_ACCESS_KEY": "minio-secret",
        "AWS_STORAGE_BUCKET_NAME": "selflink-media",
        "AWS_S3_ADDRESSING_STYLE": "path",
        "AWS_DEFAULT_ACL": None,
        "AWS_QUERYSTRING_AUTH": False,
        "STORAGES": {
            "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        },
        "DEFAULT_FILE_STORAGE": "storages.backends.s3boto3.S3Boto3Storage",
        "MEDIA_URL": "http://minio:9000/selflink-media/",
    }

    with override_settings(**s3_settings):
        default_storage._wrapped = None
        user = get_user_model().objects.create_user(
            email="media-s3@example.com",
            password="pass12345",
            handle="media_s3",
            name="Media S3",
        )
        thread = Thread.objects.create(created_by=user)
        message = Message.objects.create(
            thread=thread,
            sender=user,
            type=Message.Type.IMAGE,
        )
        attachment = MessageAttachment.objects.create(
            message=message,
            file="messages/attachments/test.png",
            type=MessageAttachment.AttachmentType.IMAGE,
            mime_type="image/png",
        )

        assert settings.STORAGE_BACKEND == "s3"
        assert settings.STORAGES["default"]["BACKEND"].endswith("S3Boto3Storage")
        url = attachment.file.url
        default_storage._wrapped = None

    default_storage._wrapped = None

    assert url.startswith("http")
    assert "minio:9000" in url
    assert "selflink-media" in url
