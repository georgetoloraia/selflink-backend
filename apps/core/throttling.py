from __future__ import annotations

from rest_framework.throttling import SimpleRateThrottle


class IPRateThrottle(SimpleRateThrottle):
    """
    IP-based throttle applied globally in addition to user/anon throttles.
    """

    scope = "ip"

    def get_cache_key(self, request, view) -> str | None:  # type: ignore[override]
        ident = self.get_ident(request)
        if ident is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}
