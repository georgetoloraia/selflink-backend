from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.messaging.models import Message, MessageAttachment


def register_and_login(client: APIClient, email: str, handle: str) -> dict:
    payload = {
        "email": email,
        "handle": handle,
        "name": handle,
        "password": "strongpassword",
    }
    client.post("/api/v1/auth/register", payload, format="json")
    login = client.post("/api/v1/auth/login", {"email": email, "password": payload["password"]}, format="json")
    token = login.data["token"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return login.data["user"]


class MessageAttachmentTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.sender_client = APIClient()
        self.recipient_client = APIClient()
        self.sender = register_and_login(self.sender_client, "attach-sender@example.com", "attachsender")
        self.recipient = register_and_login(
            self.recipient_client, "attach-recipient@example.com", "attachrecipient"
        )

    def _create_thread(self) -> str:
        response = self.sender_client.post(
            "/api/v1/messaging/threads/direct/",
            {"user_id": self.recipient["id"]},
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        return str(response.data["id"])

    def test_send_message_with_single_image(self) -> None:
        thread_id = self._create_thread()
        file = SimpleUploadedFile("photo.png", b"pngdata", content_type="image/png")
        response = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "hello", "client_uuid": "img-1", "attachments": [file]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attachments = response.data.get("attachments", [])
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["type"], MessageAttachment.AttachmentType.IMAGE)

    def test_send_message_with_multiple_images_limits_to_four(self) -> None:
        thread_id = self._create_thread()
        files = [
            SimpleUploadedFile(f"photo{i}.png", b"pngdata", content_type="image/png")
            for i in range(4)
        ]
        response = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "hello", "client_uuid": "img-4", "attachments": files},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data.get("attachments", [])), 4)

        too_many = files + [
            SimpleUploadedFile("extra.png", b"pngdata", content_type="image/png"),
        ]
        response2 = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "too many", "client_uuid": "img-5", "attachments": too_many},
            format="multipart",
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_message_with_video_or_mixed_types(self) -> None:
        thread_id = self._create_thread()
        video = SimpleUploadedFile("clip.mp4", b"mp4data", content_type="video/mp4")
        video_resp = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "video", "client_uuid": "vid-1", "attachments": [video]},
            format="multipart",
        )
        self.assertEqual(video_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(video_resp.data.get("attachments", [])[0]["type"], MessageAttachment.AttachmentType.VIDEO)

        mixed_resp = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {
                "text": "mixed",
                "client_uuid": "mix-1",
                "attachments": [
                    SimpleUploadedFile("mix.png", b"pngdata", content_type="image/png"),
                    SimpleUploadedFile("mix.mp4", b"mp4data", content_type="video/mp4"),
                ],
            },
            format="multipart",
        )
        self.assertEqual(mixed_resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sync_returns_attachments(self) -> None:
        thread_id = self._create_thread()
        file = SimpleUploadedFile("photo.png", b"pngdata", content_type="image/png")
        send_resp = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "sync me", "client_uuid": "sync-1", "attachments": [file]},
            format="multipart",
        )
        self.assertEqual(send_resp.status_code, status.HTTP_201_CREATED)
        message_id = int(send_resp.data["id"])

        sync = self.recipient_client.get(f"/api/v1/messaging/threads/{thread_id}/sync/?since={message_id-1}")
        self.assertEqual(sync.status_code, status.HTTP_200_OK)
        messages = sync.data.get("messages", [])
        self.assertTrue(messages)
        self.assertEqual(len(messages[0].get("attachments", [])), 1)

    def test_dedupe_does_not_duplicate_attachments(self) -> None:
        thread_id = self._create_thread()
        file = SimpleUploadedFile("photo.png", b"pngdata", content_type="image/png")
        payload = {"text": "dedupe", "client_uuid": "dedupe-1", "attachments": [file]}
        first = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            payload,
            format="multipart",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            payload,
            format="multipart",
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK)

        messages = Message.objects.filter(thread_id=int(thread_id))
        self.assertEqual(messages.count(), 1)
        attachments = MessageAttachment.objects.filter(message=messages.first())
        self.assertEqual(attachments.count(), 1)
