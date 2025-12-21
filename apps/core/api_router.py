from django.urls import include, path, re_path

from .views import HomeHighlightsView

urlpatterns = [
    re_path(r"^home/highlights/?$", HomeHighlightsView.as_view(), name="home-highlights"),
    path("auth/", include("apps.users.urls")),
    path("", include("apps.users.profile_urls")),
    path("", include("apps.social.urls")),
    path("", include("apps.messaging.urls")),
    path("messaging/", include("apps.messaging.urls")),
    path("", include("apps.mentor.urls")),
    path("", include("apps.astro.urls")),
    path("", include("apps.profile.urls")),
    path("", include("apps.matching.urls")),
    path("", include("apps.matrix.urls")),
    path("", include("apps.media.urls")),
    path("", include("apps.search.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.audit.urls")),
    path("", include("apps.contrib_rewards.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.moderation.urls")),
    path("", include("apps.feed.urls")),
    path("", include("apps.reco.api.urls")),
]
