from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.messaging.models import Message
from apps.users.models import User


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


class MessagingReliabilityTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.sender_client = APIClient()
        self.recipient_client = APIClient()
        self.sender = register_and_login(self.sender_client, "sender@example.com", "sender")
        self.recipient = register_and_login(self.recipient_client, "recipient@example.com", "recipient")

    def _create_direct_thread(self) -> str:
        response = self.sender_client.post(
            "/api/v1/messaging/threads/direct/",
            {"user_id": self.recipient["id"]},
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        return str(response.data["id"])

    def test_message_ack_marks_delivered(self) -> None:
        thread_id = self._create_direct_thread()
        send_response = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "Hello", "client_uuid": "uuid-123"},
            format="json",
        )
        self.assertEqual(send_response.status_code, status.HTTP_201_CREATED)
        message_id = int(send_response.data["id"])

        ack_response = self.recipient_client.post(
            f"/api/v1/messaging/messages/{message_id}/ack/",
            {"status": "delivered"},
            format="json",
        )
        self.assertEqual(ack_response.status_code, status.HTTP_200_OK)
        message = Message.objects.get(id=message_id)
        self.assertEqual(message.status, Message.Status.DELIVERED)
        self.assertIsNotNone(message.delivered_at)

    def test_client_uuid_prevents_duplicates(self) -> None:
        thread_id = self._create_direct_thread()
        payload = {"thread": thread_id, "body": "Dedup me", "client_uuid": "uuid-dedupe"}
        first = self.sender_client.post("/api/v1/messaging/messages/", payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.sender_client.post("/api/v1/messaging/messages/", payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["id"], second.data["id"])

        count = Message.objects.filter(thread_id=int(thread_id), sender_id=self.sender["id"]).count()
        self.assertEqual(count, 1)

    def test_sync_returns_newer_messages_with_status(self) -> None:
        thread_id = self._create_direct_thread()
        m1 = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "First", "client_uuid": "uuid-1"},
            format="json",
        ).data
        m2 = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "Second", "client_uuid": "uuid-2"},
            format="json",
        ).data

        ack = self.recipient_client.post(
            f"/api/v1/messaging/messages/{m2['id']}/ack/",
            {"status": "delivered"},
            format="json",
        )
        self.assertEqual(ack.status_code, status.HTTP_200_OK)
        read_response = self.recipient_client.post(f"/api/v1/messaging/threads/{thread_id}/read/")
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)

        sync = self.recipient_client.get(f"/api/v1/messaging/threads/{thread_id}/sync/?since={m1['id']}")
        self.assertEqual(sync.status_code, status.HTTP_200_OK)
        messages = sync.data.get("messages", [])
        self.assertEqual(len(messages), 1)
        returned = messages[0]
        self.assertEqual(str(returned["id"]), str(m2["id"]))
        self.assertEqual(returned["status"], Message.Status.READ)
        self.assertIsNotNone(returned.get("delivered_at"))
        self.assertIsNotNone(returned.get("read_at"))
