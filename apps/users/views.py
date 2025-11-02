from __future__ import annotations

from django.db.models import Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.social.models import Follow
from services.reco.jobs import rebuild_user_timeline

from .models import Device, User
from .serializers import (
    DeviceSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user, context={"request": request}).data,
        }
        return Response(data, status=status.HTTP_200_OK)


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
