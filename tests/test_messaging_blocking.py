from __future__ import annotations

from unittest import mock

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.users.models import Block, Mute


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


class MessagingBlockMuteTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.sender_client = APIClient()
        self.recipient_client = APIClient()
        self.sender = register_and_login(self.sender_client, "blocker@example.com", "blocker")
        self.recipient = register_and_login(self.recipient_client, "blocked@example.com", "blocked")

    def _create_direct_thread(self) -> str:
        response = self.sender_client.post(
            "/api/v1/messaging/threads/direct/",
            {"user_id": self.recipient["id"]},
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        return str(response.data["id"])

    def test_block_prevents_direct_creation_and_sending(self) -> None:
        Block.objects.create(user_id=self.sender["id"], target_id=self.recipient["id"])
        create = self.sender_client.post(
            "/api/v1/messaging/threads/direct/",
            {"user_id": self.recipient["id"]},
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_403_FORBIDDEN)

        Block.objects.filter(user_id=self.sender["id"], target_id=self.recipient["id"]).delete()
        thread_id = self._create_direct_thread()
        Block.objects.create(user_id=self.recipient["id"], target_id=self.sender["id"])
        send = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "blocked", "client_uuid": "block-1"},
            format="multipart",
        )
        self.assertEqual(send.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch("apps.notifications.consumers.notify_new_message_task.delay")
    def test_mute_skips_push_notifications(self, notify_delay) -> None:
        thread_id = self._create_direct_thread()
        first = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "ping", "client_uuid": "mute-0"},
            format="multipart",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        notify_delay.assert_called_once()

        Mute.objects.create(user_id=self.recipient["id"], target_id=self.sender["id"])
        second = self.sender_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "still allowed", "client_uuid": "mute-1"},
            format="multipart",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        notify_delay.assert_called_once()  # no new push task for muted recipient
