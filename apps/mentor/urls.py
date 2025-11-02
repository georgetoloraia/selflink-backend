from rest_framework.routers import DefaultRouter

from .views import DailyTaskViewSet, MentorProfileViewSet, MentorSessionViewSet

router = DefaultRouter()
router.register(r"mentor/sessions", MentorSessionViewSet, basename="mentor-session")
router.register(r"mentor/tasks", DailyTaskViewSet, basename="mentor-task")
router.register(r"mentor/profile", MentorProfileViewSet, basename="mentor-profile")

urlpatterns = router.urls
