from django.urls import path

from apps.feed.views import FeedHealthView, ForYouFeedView, ForYouVideosFeedView, FollowingFeedView

urlpatterns = [
    path("feed/for_you/", ForYouFeedView.as_view(), name="feed-for-you"),
    path("feed/for_you_videos/", ForYouVideosFeedView.as_view(), name="feed-for-you-videos"),
    path("feed/following/", FollowingFeedView.as_view(), name="feed-following"),
    path("feed/health/", FeedHealthView.as_view(), name="feed-health"),
]
