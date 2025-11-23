from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

PLACEHOLDER_REPLY = (
    "This is a placeholder answer from SelfLink AI Mentor. LLM server is not configured yet."
)

# --- Performance / speed tuning constants ---
DEFAULT_TIMEOUT = int(os.getenv("MENTOR_LLM_TIMEOUT", "120"))  # წამებში
MAX_TOKENS = int(os.getenv("MENTOR_LLM_MAX_TOKENS", "180"))   # პასუხის მაქს. სიგრძე (~საშუალო პასუხი)
MAX_PROMPT_CHARS = int(os.getenv("MENTOR_LLM_MAX_PROMPT_CHARS", "4000"))  # prompt truncate
MAX_MESSAGES = int(os.getenv("MENTOR_LLM_MAX_MESSAGES", "12"))  # history-ს მაქს. სიგრძე


def _trim_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    შევზღუდოთ history და prompt-ის სიგრძე, რომ მოდელი არ „გაიგიჟოს“.

    წესები:
    - ვუტოვებთ ყველა system მესიჯს.
    - user/assistant მესიჯებიდან ვტოვებთ მხოლოდ ბოლო MAX_MESSAGES-ს.
    - თუ ჯამური content ძალიან დიდია, prompt-ში ვიყენებთ მხოლოდ ბოლო MAX_PROMPT_CHARS სიმბოლოს.
    """
    system_msgs: List[Dict[str, Any]] = []
    other_msgs: List[Dict[str, Any]] = []

    for m in messages:
        role = m.get("role", "user")
        if role == "system":
            system_msgs.append(m)
        else:
            other_msgs.append(m)

    # შევზღუდოთ user/assistant მესიჯების რაოდენობა
    other_msgs = other_msgs[-MAX_MESSAGES:]

    trimmed = system_msgs + other_msgs

    # თუ ჯამური content ძალიან გრძელია, ვჭრით ტექსტურად (მთავრობაში დავტოვოთ ბოლო ნაწილი)
    all_text = "".join(str(m.get("content", "")) for m in trimmed)
    if len(all_text) <= MAX_PROMPT_CHARS:
        return trimmed

    # ძალიან მარტივი სტრატეგია: ბოლო MAX_PROMPT_CHARS სიმბოლო მთლიანად
    overflow = len(all_text) - MAX_PROMPT_CHARS
    cut_from = overflow

    new_trimmed: List[Dict[str, Any]] = []
    acc = 0
    for m in trimmed:
        content = str(m.get("content", ""))
        if not content:
            new_trimmed.append(m)
            continue

        start = 0
        end = len(content)

        # content-ის რომელ ნაწილს ჩავრთავთ?
        if acc + end <= cut_from:
            # მთლიანად გადავდივართ, სანამ ჯერ ჭრილობამდე მივალთ
            acc += end
            # ეს მესიჯი მთლიანად "გავუშვათ"
            continue
        elif acc < cut_from < acc + end:
            # ამას ნაწილობრივ უნდა მოვჭრათ
            offset = cut_from - acc
            content = content[offset:]
            acc += end
        else:
            acc += end

        new_trimmed.append({**m, "content": content})

    return new_trimmed


def _build_prompt_from_messages(messages: List[Dict[str, Any]]) -> str:
    """
    როცა /api/chat არ არსებობს და გვჭირდება /api/generate,
    ვაქცევთ messages-ს უბრალო ტექსტურ prompt-ად.
    ბოლოს ვამატებთ "Assistant:"-ს, რომ მოდელმა იცოდეს, ვისი რიგია.
    """
    trimmed = _trim_messages(messages)

    parts: List[str] = []
    for msg in trimmed:
        role = msg.get("role", "user")
        content = str(msg.get("content", "")).strip()
        if not content:
            continue

        if role == "system":
            parts.append(f"System: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
        else:
            parts.append(f"User: {content}")

    parts.append("Assistant:")
    prompt = "\n".join(parts)

    # დამატებით უსაფრთხოება prompt სიგრძეზე
    if len(prompt) > MAX_PROMPT_CHARS:
        prompt = prompt[-MAX_PROMPT_CHARS:]

    return prompt


def chat(messages: List[Dict[str, Any]]) -> str:
    """
    Send chat messages to the configured LLM server (Ollama).

    სცდილობს:
      1) Ollama /api/chat ფორმატს (ოპტიმიზირებული prompt-ით)
      2) თუ /api/chat აბრუნებს 404-ს → სცდილობს /api/generate-ს

    messages ფორმატი:
    [
        {"role": "system" | "user" | "assistant", "content": "..."},
        ...
    ]
    """
    base_url = os.getenv("MENTOR_LLM_BASE_URL")
    model = os.getenv("MENTOR_LLM_MODEL", "llama3.2:1b")  # ან selflink-mentor, phi3:mini და ა.შ.

    if not base_url:
        return PLACEHOLDER_REPLY

    base_url = base_url.rstrip("/")

    # ჯერ history და prompt შევჭრათ, რომ სწრაფად იმუშაოს
    trimmed_messages = _trim_messages(messages)

    # --- 1) ვცადოთ /api/chat ---
    try:
        chat_url = f"{base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": trimmed_messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": MAX_TOKENS,
            },
        }

        response = requests.post(chat_url, json=payload, timeout=DEFAULT_TIMEOUT)

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

    # --- 2) fallback: ვცადოთ /api/generate ---
    try:
        generate_url = f"{base_url}/api/generate"
        prompt = _build_prompt_from_messages(messages)

        gen_payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": MAX_TOKENS,
            },
        }

        response = requests.post(generate_url, json=gen_payload, timeout=DEFAULT_TIMEOUT)
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
