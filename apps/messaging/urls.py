from rest_framework.routers import DefaultRouter

from .views import MessageViewSet, ThreadViewSet

router = DefaultRouter()
router.register(r"threads", ThreadViewSet, basename="thread")
router.register(r"messages", MessageViewSet, basename="message")

urlpatterns = router.urls
