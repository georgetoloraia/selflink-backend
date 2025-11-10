from __future__ import annotations

from django.conf import settings
from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.social.models import Follow
from services.reco.jobs import rebuild_user_timeline

from .models import Device, PersonalMapProfile, User
from .serializers import (
    DeviceSerializer,
    LoginSerializer,
    PersonalMapProfileSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)


def _build_auth_payload(user: User, request: Request, message: str = "") -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "token": str(refresh.access_token),
        "refreshToken": str(refresh),
        "user": UserSerializer(user, context={"request": request}).data,
        "message": message or "",
    }


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        payload = _build_auth_payload(user, request, message="Registration successful.")
        headers = self.get_success_headers(serializer.data)
        return Response(payload, status=status.HTTP_201_CREATED, headers=headers)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        payload = _build_auth_payload(user, request, message="Login successful.")
        return Response(payload, status=status.HTTP_200_OK)


class TokenRefreshAPIView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code != status.HTTP_200_OK:
            return response
        data = response.data or {}
        payload = {
            "token": data.get("access"),
            "refreshToken": data.get("refresh"),
            "message": "Token refreshed.",
        }
        return Response(payload, status=response.status_code)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().select_related("settings")
    serializer_class = UserSerializer
    lookup_field = "id"
    lookup_url_kwarg = "id"
    search_fields = ["handle", "name", "email"]

    def get_queryset(self):  # type: ignore[override]
        queryset = super().get_queryset()
        search = self.request.query_params.get("q")
        if search:
            queryset = queryset.filter(
                Q(handle__icontains=search)
                | Q(name__icontains=search)
                | Q(email__icontains=search)
            )
        return queryset

    @action(methods=["get", "patch"], detail=False, url_path="me")
    def me(self, request: Request) -> Response:
        user = request.user
        if request.method.lower() == "get":
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        serializer = ProfileUpdateSerializer(
            user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user, context={"request": request}).data)

    @action(methods=["post", "delete"], detail=True, url_path="follow")
    def follow(self, request: Request, *args, **kwargs) -> Response:
        target = self.get_object()
        if target == request.user:
            return Response({"detail": "Cannot follow yourself"}, status=status.HTTP_400_BAD_REQUEST)
        if request.method.lower() == "post":
            follow, _ = Follow.objects.get_or_create(follower=request.user, followee=target)
            rebuild_user_timeline(request.user.id)
            return Response({"following": True})
        Follow.objects.filter(follower=request.user, followee=target).delete()
        rebuild_user_timeline(request.user.id)
        return Response({"following": False})

    @action(detail=True, methods=["get"], url_path="followers")
    def followers(self, request: Request, *args, **kwargs) -> Response:
        target = self.get_object()
        qs = Follow.objects.filter(followee=target).select_related("follower")
        users = [follow.follower for follow in qs]
        serializer = UserSerializer(users, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="following")
    def following(self, request: Request, *args, **kwargs) -> Response:
        target = self.get_object()
        qs = Follow.objects.filter(follower=target).select_related("followee")
        users = [follow.followee for follow in qs]
        serializer = UserSerializer(users, many=True, context={"request": request})
        return Response(serializer.data)


class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer

    def get_queryset(self):  # type: ignore[override]
        return Device.objects.filter(user=self.request.user)

    def perform_create(self, serializer: DeviceSerializer) -> None:  # type: ignore[override]
        serializer.save(user=self.request.user)


class SocialLoginBaseView(SocialLoginView):
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = super().post(request, *args, **kwargs)
        if response.status_code >= 400:
            return response
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return response
        payload = _build_auth_payload(user, request, message="Social login successful.")
        return Response(payload, status=response.status_code)


class GoogleSocialLoginView(SocialLoginBaseView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.SOCIAL_AUTH_REDIRECT_URIS["google"]


class FacebookSocialLoginView(SocialLoginBaseView):
    adapter_class = FacebookOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.SOCIAL_AUTH_REDIRECT_URIS["facebook"]


class GithubSocialLoginView(SocialLoginBaseView):
    adapter_class = GitHubOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.SOCIAL_AUTH_REDIRECT_URIS["github"]


class PersonalMapProfileView(generics.GenericAPIView):
    serializer_class = PersonalMapProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile = PersonalMapProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response(self._empty_payload(request))
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    def put(self, request: Request, *args, **kwargs) -> Response:
        return self._write_profile(request, partial=False)

    def patch(self, request: Request, *args, **kwargs) -> Response:
        return self._write_profile(request, partial=True)

    def _write_profile(self, request: Request, partial: bool) -> Response:
        profile = PersonalMapProfile.objects.filter(user=request.user).first()
        serializer = self.get_serializer(
            profile,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def _empty_payload(self, request: Request) -> dict:
        return {
            "email": request.user.email,
            "first_name": "",
            "last_name": "",
            "birth_date": None,
            "birth_time": None,
            "birth_place_country": "",
            "birth_place_city": "",
            "avatar_image": None,
            "is_complete": False,
        }
