# from __future__ import annotations

# import logging
# import os
# from typing import Any, Dict, List

# import requests

# logger = logging.getLogger(__name__)

# PLACEHOLDER_REPLY = (
#     "This is a placeholder answer from SelfLink AI Mentor. LLM server is not configured yet."
# )


# def chat(messages: List[Dict[str, Any]]) -> str:
#     """
#     Send chat messages to the configured LLM server.
#     Falls back to a placeholder when the server is not configured or errors occur.
#     """
#     base_url = os.getenv("MENTOR_LLM_BASE_URL")
#     model = os.getenv("MENTOR_LLM_MODEL", "selflink-mentor")

#     if not base_url:
#         return PLACEHOLDER_REPLY

#     try:
#         response = requests.post(
#             f"{base_url.rstrip('/')}/v1/chat/completions",
#             json={"model": model, "messages": messages},
#             timeout=15,
#         )
#         response.raise_for_status()
#         payload = response.json()
#         content = (
#             payload.get("choices", [{}])[0]
#             .get("message", {})
#             .get("content")
#         )
#         if content:
#             return content
#     except Exception as exc:  # pragma: no cover - fallback path
#         logger.warning("Mentor LLM chat failed: %s", exc, exc_info=True)

#     return PLACEHOLDER_REPLY




from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

PLACEHOLDER_REPLY = (
    "This is a placeholder answer from SelfLink AI Mentor. LLM server is not configured yet."
)


def _build_prompt_from_messages(messages: List[Dict[str, Any]]) -> str:
    """
    როცა /api/chat არ არსებობს და გვჭირდება /api/generate,
    ვაქცევთ messages-ს უბრალო ტექსტურ prompt-ად.
    """
    parts: List[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content:
            continue

        if role == "system":
            parts.append(f"System: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
        else:
            parts.append(f"User: {content}")

    parts.append("Assistant:")
    return "\n".join(parts)


def chat(messages: List[Dict[str, Any]]) -> str:
    """
    Send chat messages to the configured LLM server.

    სცდილობს:
      1) Ollama /api/chat ფორმატს
      2) თუ /api/chat აბრუნებს 404-ს → სცდილობს /api/generate-ს

    messages ფორმატი:
    [
        {"role": "system" | "user" | "assistant", "content": "..."},
        ...
    ]
    """
    base_url = os.getenv("MENTOR_LLM_BASE_URL")
    model = os.getenv("MENTOR_LLM_MODEL", "llama3.2:1b")  # შეცვალე თუ შენს მოდელს სხვა სახელი აქვს

    if not base_url:
        return PLACEHOLDER_REPLY

    base_url = base_url.rstrip("/")

    # --- 1) ვცადოთ /api/chat ---
    try:
        chat_url = f"{base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                # სურვილისამებრ:
                # "temperature": 0.7,
                # "num_predict": 512,
            },
        }

        response = requests.post(chat_url, json=payload, timeout=60)

        # თუ კონკრეტულად 404 მოვიდა → გადავდივართ /api/generate-ზე
        if response.status_code == 404:
            logger.info(
                "Mentor LLM: /api/chat returned 404, falling back to /api/generate"
            )
            raise FileNotFoundError("/api/chat not found")

        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content")
        if content:
            return content

    except FileNotFoundError:
        # სპეციალურად აქამდე მოვიყვანეთ, რომ გადახტეს /api/generate-ზე
        pass
    except Exception as exc:
        # სხვა ერორი /api/chat-ზე → ლოგავდეთ და მაინც ვეცადოთ /api/generate-ს
        logger.warning("Mentor LLM /api/chat failed: %s", exc, exc_info=True)

    # --- 2) ვცადოთ /api/generate ---
    try:
        generate_url = f"{base_url}/api/generate"
        prompt = _build_prompt_from_messages(messages)

        gen_payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            # "options": {"temperature": 0.7, "num_predict": 512},
        }

        response = requests.post(generate_url, json=gen_payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Ollama /api/generate (stream=False) აბრუნებს:
        # {"model": "...", "created_at": "...", "response": "....", "done": true, ...}
        content = data.get("response")
        if content:
            return content

    except Exception as exc:  # pragma: no cover - fallback path
        logger.warning("Mentor LLM /api/generate failed: %s", exc, exc_info=True)

    return PLACEHOLDER_REPLY
