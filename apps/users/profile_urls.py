from rest_framework.routers import DefaultRouter

from .views import DeviceViewSet, UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"devices", DeviceViewSet, basename="device")

urlpatterns = router.urls
