from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DeviceViewSet, PersonalMapProfileView, UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"devices", DeviceViewSet, basename="device")

urlpatterns = router.urls + [
    path("me/profile/", PersonalMapProfileView.as_view(), name="me-profile"),
]
