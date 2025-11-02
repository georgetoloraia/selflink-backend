from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CommentViewSet, FeedView, GiftViewSet, PostViewSet

router = DefaultRouter()
router.register(r"posts", PostViewSet, basename="post")
router.register(r"comments", CommentViewSet, basename="comment")
router.register(r"gifts", GiftViewSet, basename="gift")

urlpatterns = router.urls + [
    path("feed/home/", FeedView.as_view(), name="feed-home"),
]
