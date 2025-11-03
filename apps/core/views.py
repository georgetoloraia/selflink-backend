from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HomeHighlightsView(APIView):
    permission_classes = [permissions.AllowAny]

    _HIGHLIGHTS_PAYLOAD = {
        "hero": {
            "badge": "Year of the Horse Prelude",
            "title": "Attune to the signal of your higher self.",
            "description": (
                "As the Year of the Horse approaches, SelfLink braids in vibrant rose auroras to "
                "spark courageous motion. Every interaction invites you deeper into presence, trust, "
                "and luminous creativity."
            ),
            "primaryCta": {"label": "Begin the Journey", "path": "/register"},
            "secondaryCta": {"label": "Converse with Mentor", "path": "/mentor"},
        },
        "features": [
            {
                "id": "soulmatch",
                "title": "SoulMatch Resonance",
                "subtitle": "Find aligned peers on energetic wavelength",
                "description": (
                    "Decode your resonance signature and connect to seekers exploring the same "
                    "dimension of growth."
                ),
                "cta": {"label": "Explore matches", "path": "/soul-match"},
            },
            {
                "id": "mentor",
                "title": "AI Mentor Guidance",
                "subtitle": "Conversational clarity in real-time",
                "description": (
                    "Your mentor listens between the lines, reflects your truth, and surfaces "
                    "next-step practices."
                ),
                "cta": {"label": "Meet the mentor", "path": "/mentor"},
            },
            {
                "id": "growth",
                "title": "Growth Pathway",
                "subtitle": "Micro rituals, macro transformation",
                "description": (
                    "Curate gentle daily practices tuned to your emotional spectrum with adaptive pacing."
                ),
                "cta": {"label": "Design your path", "path": "/growth-path"},
            },
        ],
        "celebration": {
            "title": "Year of the Horse Illumination",
            "copy": (
                "February’s portal ushers in spirited momentum. Join the collective circle to weave "
                "reddish-pink resonance into your practice and receive custom mentor prompts for the "
                "new zodiac cycle."
            ),
            "tags": ["Opening circle · Feb 9", "Global livestream"],
            "cta": "Reserve my spot",
        },
    }

    def get(self, request, *args, **kwargs) -> Response:
        return Response(self._HIGHLIGHTS_PAYLOAD, status=status.HTTP_200_OK)
