from django.urls import path

from apps.feed.views import FeedHealthView, ForYouFeedView, FollowingFeedView

urlpatterns = [
    path("feed/for_you/", ForYouFeedView.as_view(), name="feed-for-you"),
    path("feed/following/", FollowingFeedView.as_view(), name="feed-following"),
    path("feed/health/", FeedHealthView.as_view(), name="feed-health"),
]
