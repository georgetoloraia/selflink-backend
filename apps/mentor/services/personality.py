from __future__ import annotations

from pathlib import Path

BASE_PERSONA_CACHE: dict[str, str] = {}


def _load_persona_file(filename: str) -> str:
    if filename in BASE_PERSONA_CACHE:
        return BASE_PERSONA_CACHE[filename]

    base_dir = Path(__file__).resolve().parent.parent  # apps/mentor
    persona_path = base_dir / "persona" / filename
    try:
        text = persona_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        text = "You are SelfLink AI Mentor, a warm and supportive guide."
    BASE_PERSONA_CACHE[filename] = text
    return text


def get_base_persona_prompt(language: str | None = None) -> str:
    """
    Return the base persona prompt, optionally routed by language.
    Files live in apps/mentor/persona/*.txt so prompts can be updated without code changes.
    """
    if language and language.startswith("ka"):
        filename = "base_ka.txt"
    elif language and language.startswith("ru"):
        filename = "base_ru.txt"
    else:
        filename = "base_en.txt"
    return _load_persona_file(filename)


def _get_daily_persona_prompt(language: str | None = None) -> str:
    if language and language.startswith("ka"):
        filename = "daily_ka.txt"
    elif language and language.startswith("ru"):
        filename = "daily_ru.txt"
    else:
        filename = "daily_en.txt"
    return _load_persona_file(filename)


def get_prompt(language: str | None = None, mode: str | None = None) -> str:
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
            # Fallback to base persona if daily file missing
            pass
    return get_base_persona_prompt(language)
