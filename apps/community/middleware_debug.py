from __future__ import annotations

import os

from django.conf import settings


def _db_fingerprint() -> str:
    cfg = settings.DATABASES.get("default", {})
    host = cfg.get("HOST") or "local"
    name = cfg.get("NAME") or "db"
    return f"{host}:{name}"


class CommunityDebugHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/v1/community/"):
            response["X-SL-Instance"] = os.environ.get("HOSTNAME") or os.uname().nodename
            response["X-SL-DB"] = _db_fingerprint()
        return response
