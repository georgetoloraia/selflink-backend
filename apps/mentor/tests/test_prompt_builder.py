from __future__ import annotations

from types import SimpleNamespace

from apps.mentor.services import prompt_builder


def test_build_messages_includes_system_context_and_history():
    user = SimpleNamespace(
        birth_date="1990-01-01",
        birth_time="12:30",
        birth_place="Tbilisi, Georgia",
        astro_profile=SimpleNamespace(sun="Aries", moon="Gemini", ascendant="Libra"),
        matrix_data=SimpleNamespace(life_path="7", traits={"primary_trait": "Seeker"}),
    )
    history = [
        {"role": "user", "content": "Old question"},
        {"role": "assistant", "content": "Old answer"},
    ]

    messages = prompt_builder.build_messages(
        user=user,
        language="en",
        history=history,
        user_text="New message",
    )

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "system"
    # history preserved
    assert messages[2:4] == history
    # latest user message goes last
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "New message"
    # astro context should mention data from the user
    assert "Birth date" in messages[1]["content"]
    assert "Aries" in messages[1]["content"]
    assert "Life path" in messages[1]["content"]


def test_build_messages_handles_missing_fields():
    user = SimpleNamespace()  # no astro data

    messages = prompt_builder.build_messages(
        user=user,
        language="en",
        history=[],
        user_text="Hello",
    )

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "system"
    assert messages[-1]["content"] == "Hello"
    assert "(No astro or matrix data" in messages[1]["content"]
