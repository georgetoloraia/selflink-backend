from django.urls import path

from apps.feed.views import ForYouFeedView, FollowingFeedView

urlpatterns = [
    path("feed/for_you/", ForYouFeedView.as_view(), name="feed-for-you"),
    path("feed/following/", FollowingFeedView.as_view(), name="feed-following"),
]
