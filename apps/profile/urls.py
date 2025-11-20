from django.urls import path

from apps.profile.views import MeProfileView

urlpatterns = [
    path("profile/me/", MeProfileView.as_view(), name="profile-me"),
]
