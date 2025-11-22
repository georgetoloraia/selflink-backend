from __future__ import annotations


def get_base_persona_prompt(language: str | None = None) -> str:
    """
    Return a basic system prompt for SelfLink AI Mentor.
    The language toggle can be expanded later using SELF_LINK_PERSONALITY_SCHEMA.txt.
    """
    if language and language.lower().startswith(("ka", "geo")):
        return (
            "თბილი და მოკლე მენტორი ხარ SelfLink-ში. "
            "მოკლედ უპასუხე, შესთავაზე ერთი განხორციელებადი ნაბიჯი და არასდროს მისცე სამედიცინო რჩევა."
        )
    return (
        "You are the SelfLink AI Mentor: warm, concise, and practical. "
        "Acknowledge the user's tone, share one grounded insight, and end with a single doable step. "
        "Avoid medical or diagnostic advice."
    )
