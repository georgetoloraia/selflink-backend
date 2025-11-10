from django.urls import re_path

from .views import (
    FacebookSocialLoginView,
    GithubSocialLoginView,
    GoogleSocialLoginView,
    LoginView,
    RegisterView,
    TokenRefreshAPIView,
)

urlpatterns = [
    re_path(r"^register/?$", RegisterView.as_view(), name="auth-register"),
    re_path(r"^login/?$", LoginView.as_view(), name="auth-login"),
    re_path(r"^refresh/?$", TokenRefreshAPIView.as_view(), name="auth-refresh"),
    re_path(
        r"^social/google/callback/?$",
        GoogleSocialLoginView.as_view(),
        name="auth-social-google",
    ),
    re_path(
        r"^social/facebook/callback/?$",
        FacebookSocialLoginView.as_view(),
        name="auth-social-facebook",
    ),
    re_path(
        r"^social/github/callback/?$",
        GithubSocialLoginView.as_view(),
        name="auth-social-github",
    ),
]
