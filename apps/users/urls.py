from django.urls import re_path

from .views import LoginView, RegisterView, TokenRefreshAPIView

urlpatterns = [
    re_path(r"^register/?$", RegisterView.as_view(), name="auth-register"),
    re_path(r"^login/?$", LoginView.as_view(), name="auth-login"),
    re_path(r"^refresh/?$", TokenRefreshAPIView.as_view(), name="auth-refresh"),
]
