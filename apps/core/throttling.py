from __future__ import annotations

from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


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


class ScopedUserRateThrottle(ScopedRateThrottle):
    """
    Per-user scoped rate limit (requires view.throttle_scope).
    """

    def get_cache_key(self, request, view) -> str | None:  # type: ignore[override]
        scope = getattr(view, "throttle_scope", None)
        if not scope or not getattr(request.user, "is_authenticated", False):
            return None
        self.scope = f"user:{scope}"
        ident = request.user.pk
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ScopedIPRateThrottle(ScopedRateThrottle):
    """
    Per-IP scoped rate limit (requires view.throttle_scope).
    """

    def get_cache_key(self, request, view) -> str | None:  # type: ignore[override]
        scope = getattr(view, "throttle_scope", None)
        if not scope:
            return None
        self.scope = f"ip:{scope}"
        ident = self.get_ident(request)
        if ident is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}
