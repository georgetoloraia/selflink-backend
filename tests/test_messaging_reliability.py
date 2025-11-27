from __future__ import annotations

import time

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.messaging.models import Message, ThreadMember
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

    def test_ack_is_forward_only_and_requires_membership(self) -> None:
        thread_id = self._create_direct_thread()
        send_response = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "Hello", "client_uuid": "ack-forward"},
            format="json",
        )
        message_id = int(send_response.data["id"])

        ack_response = self.recipient_client.post(
            f"/api/v1/messaging/messages/{message_id}/ack/",
            {"status": "delivered"},
            format="json",
        )
        self.assertEqual(ack_response.status_code, status.HTTP_200_OK)
        message = Message.objects.get(id=message_id)
        self.assertEqual(message.status, Message.Status.DELIVERED)

        # Marking read moves status forward; another ack should not regress it.
        read_response = self.recipient_client.post(f"/api/v1/messaging/threads/{thread_id}/read/")
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        message.refresh_from_db()
        self.assertEqual(message.status, Message.Status.READ)

        second_ack = self.recipient_client.post(
            f"/api/v1/messaging/messages/{message_id}/ack/",
            {"status": "delivered"},
            format="json",
        )
        self.assertEqual(second_ack.status_code, status.HTTP_200_OK)
        message.refresh_from_db()
        self.assertEqual(message.status, Message.Status.READ)

        intruder = APIClient()
        register_and_login(intruder, "intruder@example.com", "intruder")
        unauthorized_ack = intruder.post(
            f"/api/v1/messaging/messages/{message_id}/ack/",
            {"status": "delivered"},
            format="json",
        )
        self.assertEqual(unauthorized_ack.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_read_updates_last_read_and_unread_math(self) -> None:
        thread_id = self._create_direct_thread()
        messages = []
        for i in range(3):
            resp = self.sender_client.post(
                "/api/v1/messaging/messages/",
                {"thread": thread_id, "body": f"Msg {i}", "client_uuid": f"uuid-{i}"},
                format="json",
            )
            self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
            messages.append(int(resp.data["id"]))

        mark = self.recipient_client.post(
            f"/api/v1/messaging/threads/{thread_id}/read/",
            {"last_read_message_id": messages[1]},
            format="json",
        )
        self.assertEqual(mark.status_code, status.HTTP_200_OK)
        membership = ThreadMember.objects.get(thread_id=int(thread_id), user_id=self.recipient["id"])
        self.assertEqual(membership.last_read_message_id, messages[1])

        updated_messages = list(Message.objects.filter(thread_id=int(thread_id)).order_by("id"))
        self.assertEqual(updated_messages[0].status, Message.Status.READ)
        self.assertEqual(updated_messages[1].status, Message.Status.READ)
        self.assertEqual(updated_messages[2].status, Message.Status.SENT)

        threads = self.recipient_client.get("/api/v1/messaging/threads/")
        self.assertEqual(threads.status_code, status.HTTP_200_OK)
        unread_counts = {str(t["id"]): t["unread_count"] for t in threads.data}
        self.assertEqual(unread_counts.get(thread_id), 1)

    def test_sync_since_timestamp_returns_newer_messages(self) -> None:
        thread_id = self._create_direct_thread()
        first = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "First ts", "client_uuid": "ts-1"},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        since_ts = first.data["created_at"]

        time.sleep(0.01)
        second = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "Second ts", "client_uuid": "ts-2"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

        sync = self.recipient_client.get(f"/api/v1/messaging/threads/{thread_id}/sync/?since={since_ts}")
        self.assertEqual(sync.status_code, status.HTTP_200_OK)
        payload = sync.data.get("messages", [])
        self.assertEqual(len(payload), 1)
        self.assertEqual(str(payload[0]["id"]), str(second.data["id"]))

    def test_mark_read_allows_empty_body(self) -> None:
        thread_id = self._create_direct_thread()
        m1 = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "One", "client_uuid": "empty-1"},
            format="json",
        )
        self.assertEqual(m1.status_code, status.HTTP_201_CREATED)
        m2 = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "Two", "client_uuid": "empty-2"},
            format="json",
        )
        self.assertEqual(m2.status_code, status.HTTP_201_CREATED)

        mark = self.recipient_client.post(f"/api/v1/messaging/threads/{thread_id}/read/")
        self.assertIn(mark.status_code, (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT))
        membership = ThreadMember.objects.get(thread_id=int(thread_id), user_id=self.recipient["id"])
        self.assertEqual(membership.last_read_message_id, int(m2.data["id"]))

    def test_mark_read_gracefully_handles_invalid_payload_and_forward_only(self) -> None:
        thread_id = self._create_direct_thread()
        m1 = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "First", "client_uuid": "invalid-1"},
            format="json",
        )
        self.assertEqual(m1.status_code, status.HTTP_201_CREATED)
        m2 = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "Second", "client_uuid": "invalid-2"},
            format="json",
        )
        self.assertEqual(m2.status_code, status.HTTP_201_CREATED)

        bad_mark = self.recipient_client.post(
            f"/api/v1/messaging/threads/{thread_id}/read/",
            {"last_read_message_id": "not-a-number"},
            format="json",
        )
        self.assertIn(bad_mark.status_code, (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT))
        membership = ThreadMember.objects.get(thread_id=int(thread_id), user_id=self.recipient["id"])
        self.assertEqual(membership.last_read_message_id, int(m2.data["id"]))

        backward_mark = self.recipient_client.post(
            f"/api/v1/messaging/threads/{thread_id}/read/",
            {"last_read_message_id": m1.data["id"]},
            format="json",
        )
        self.assertIn(backward_mark.status_code, (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT))
        membership.refresh_from_db()
        self.assertEqual(membership.last_read_message_id, int(m2.data["id"]))
