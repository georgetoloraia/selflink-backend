from __future__ import annotations

from unittest import mock

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.messaging.models import MessageReaction


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


class MessagingReactionsRepliesTests(APITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.sender_client = APIClient()
        self.recipient_client = APIClient()
        self.sender = register_and_login(self.sender_client, "reactor@example.com", "reactor")
        self.recipient = register_and_login(self.recipient_client, "reactee@example.com", "reactee")

    def _create_thread(self) -> str:
        response = self.sender_client.post(
            "/api/v1/messaging/threads/direct/",
            {"user_id": self.recipient["id"]},
            format="json",
        )
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        return str(response.data["id"])

    def test_reaction_toggle_and_event_emission(self) -> None:
        thread_id = self._create_thread()
        message = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "React to me", "client_uuid": "react-1"},
            format="json",
        ).data
        message_id = int(message["id"])

        with mock.patch("apps.messaging.views.publish_message_reaction_event") as event_mock:
            add = self.recipient_client.post(
                f"/api/v1/messaging/messages/{message_id}/reactions/",
                {"emoji": "❤️"},
                format="json",
            )
            self.assertEqual(add.status_code, status.HTTP_200_OK)
            self.assertEqual(add.data["action"], "added")
            self.assertTrue(
                MessageReaction.objects.filter(message_id=message_id, user_id=self.recipient["id"]).exists()
            )
            event_mock.assert_called_with(
                mock.ANY,
                "❤️",
                self.recipient["id"],
                "added",
            )

            listing = self.recipient_client.get(f"/api/v1/messaging/messages/{message_id}/reactions/")
            self.assertEqual(listing.status_code, status.HTTP_200_OK)
            reactions = listing.data.get("reactions", [])
            self.assertEqual(reactions[0]["emoji"], "❤️")
            self.assertEqual(reactions[0]["count"], 1)
            self.assertTrue(reactions[0]["reacted_by_current_user"])

            remove = self.recipient_client.post(
                f"/api/v1/messaging/messages/{message_id}/reactions/",
                {"emoji": "❤️"},
                format="json",
            )
            self.assertEqual(remove.status_code, status.HTTP_200_OK)
            self.assertEqual(remove.data["action"], "removed")
            self.assertFalse(
                MessageReaction.objects.filter(message_id=message_id, user_id=self.recipient["id"]).exists()
            )

    def test_reply_validation_and_preview_serialization(self) -> None:
        thread_id = self._create_thread()
        root = self.sender_client.post(
            "/api/v1/messaging/messages/",
            {"thread": thread_id, "body": "Root message", "client_uuid": "root-1"},
            format="json",
        ).data
        root_id = int(root["id"])

        reply = self.recipient_client.post(
            f"/api/v1/messaging/threads/{thread_id}/messages/",
            {"text": "Replying", "client_uuid": "reply-1", "reply_to_message_id": root_id},
            format="multipart",
        )
        self.assertEqual(reply.status_code, status.HTTP_201_CREATED)
        reply_payload = reply.data.get("reply_to")
        self.assertIsNotNone(reply_payload)
        self.assertEqual(reply_payload["id"], str(root_id))
        self.assertEqual(reply_payload["sender_id"], self.sender["id"])
        self.assertEqual(reply_payload["text_preview"], "Root message")
        self.assertFalse(reply_payload["has_attachments"])

        third_client = APIClient()
        third_user = register_and_login(third_client, "third@example.com", "third")
        other_thread = third_client.post(
            "/api/v1/messaging/threads/direct/",
            {"user_id": self.sender["id"]},
            format="json",
        )
        self.assertIn(other_thread.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))
        other_thread_id = other_thread.data["id"]

        invalid_reply = third_client.post(
            f"/api/v1/messaging/threads/{other_thread_id}/messages/",
            {"text": "bad", "client_uuid": "reply-bad", "reply_to_message_id": root_id},
            format="multipart",
        )
        self.assertEqual(invalid_reply.status_code, status.HTTP_400_BAD_REQUEST)
