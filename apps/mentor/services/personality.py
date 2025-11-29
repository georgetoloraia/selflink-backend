from __future__ import annotations

from pathlib import Path
from typing import Optional

BASE_PERSONA_CACHE: dict[str, str] = {}
DEFAULT_PROMPT = "You are SelfLink AI Mentor, a warm and supportive guide."
PERSONA_FILES = {
    "en": "mentor_en.txt",
    "ka": "mentor_ka.txt",
    "ru": "mentor_ru.txt",
}


def _persona_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "persona"


def _load_persona_file(filename: str) -> str:
    if filename in BASE_PERSONA_CACHE:
        return BASE_PERSONA_CACHE[filename]

    persona_path = _persona_dir() / filename
    try:
        text = persona_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        text = DEFAULT_PROMPT
    BASE_PERSONA_CACHE[filename] = text
    return text


def get_persona_prompt(language: Optional[str] = None) -> str:
    """
    Return the mentor persona/system prompt for the requested language.
    Defaults to English when the language is missing or the file is absent.
    """
    lang = (language or "en").lower()
    filename = PERSONA_FILES.get(lang, PERSONA_FILES["en"])
    prompt = _load_persona_file(filename)
    if prompt != DEFAULT_PROMPT or lang == "en":
        return prompt
    # fallback to English text if the requested file was missing
    return _load_persona_file(PERSONA_FILES["en"])


def get_base_persona_prompt(language: Optional[str] = None) -> str:
    """
    Backwards-compatible helper for the base persona prompt.
    """
    if language and language.startswith("ka"):
        filename = "base_ka.txt"
    elif language and language.startswith("ru"):
        filename = "base_ru.txt"
    else:
        filename = "base_en.txt"
    return _load_persona_file(filename)


def _get_daily_persona_prompt(language: Optional[str] = None) -> str:
    if language and language.startswith("ka"):
        filename = "daily_ka.txt"
    elif language and language.startswith("ru"):
        filename = "daily_ru.txt"
    else:
        filename = "daily_en.txt"
    return _load_persona_file(filename)


def get_prompt(language: Optional[str] = None, mode: Optional[str] = None) -> str:
    """
    Public helper for fetching the SelfLink mentor persona.
    mode:
      - "daily": daily mentor persona
      - anything else: base persona
    """
    if mode == "daily":
        try:
            return _get_daily_persona_prompt(language)
        except FileNotFoundError:
            pass
    return get_base_persona_prompt(language)
