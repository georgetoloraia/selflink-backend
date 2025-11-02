from rest_framework.routers import DefaultRouter

from .views import EnforcementViewSet, ReportViewSet

router = DefaultRouter()
router.register(r"moderation/reports", ReportViewSet, basename="report")
router.register(r"moderation/enforcements", EnforcementViewSet, basename="enforcement")

urlpatterns = router.urls
