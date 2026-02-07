from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ArtifactViewSet,
    CommunityLoginAPIView,
    CommunityLogoutAPIView,
    CommunityMeAPIView,
    ProblemViewSet,
)

router = DefaultRouter()
router.register(r"community/problems", ProblemViewSet, basename="community-problems")
router.register(r"community/artifacts", ArtifactViewSet, basename="community-artifacts")

urlpatterns = router.urls + [
    path("community/auth/login/", CommunityLoginAPIView.as_view(), name="community-auth-login"),
    path("community/auth/me/", CommunityMeAPIView.as_view(), name="community-auth-me"),
    path("community/auth/logout/", CommunityLogoutAPIView.as_view(), name="community-auth-logout"),
]
