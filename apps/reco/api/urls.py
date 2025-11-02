from rest_framework.routers import DefaultRouter

from .views import SoulMatchViewSet

router = DefaultRouter()
router.register(r"soulmatch", SoulMatchViewSet, basename="soulmatch")

urlpatterns = router.urls
