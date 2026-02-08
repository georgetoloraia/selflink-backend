from __future__ import annotations


class CommunityNoStoreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/v1/community/"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
            vary = response.get("Vary", "")
            parts = [p.strip() for p in vary.split(",") if p.strip()]
            for key in ("Origin", "Authorization"):
                if key not in parts:
                    parts.append(key)
            response["Vary"] = ", ".join(parts)
        return response
