from django.urls import path
from rest_framework.routers import DefaultRouter

from .api.views import (
    DailyEntryView,
    DailyHistoryView,
    DailySessionDetailView,
    MentorChatView,
    MentorHistoryView,
)
from .views import (
    DailyMentorView,
    DailyTaskViewSet,
    MentorProfileViewSet,
    MentorSessionViewSet,
    NatalMentorView,
    SoulmatchMentorView,
)

router = DefaultRouter()
router.register(r"mentor/sessions", MentorSessionViewSet, basename="mentor-session")
router.register(r"mentor/tasks", DailyTaskViewSet, basename="mentor-task")
router.register(r"mentor/profile", MentorProfileViewSet, basename="mentor-profile")

urlpatterns = router.urls + [
    path("mentor/natal/", NatalMentorView.as_view(), name="mentor-natal"),
    path("mentor/soulmatch/<int:user_id>/", SoulmatchMentorView.as_view(), name="mentor-soulmatch"),
    path("mentor/daily/", DailyMentorView.as_view(), name="mentor-daily"),
    path("mentor/chat/", MentorChatView.as_view(), name="mentor-chat"),
    path("mentor/daily/entry/", DailyEntryView.as_view(), name="mentor-daily-entry"),
    path("mentor/daily/history/", DailyHistoryView.as_view(), name="mentor-daily-history"),
    path("mentor/daily/session/<int:session_id>/", DailySessionDetailView.as_view(), name="mentor-daily-session"),
    path("mentor/history/", MentorHistoryView.as_view(), name="mentor-history"),
]
