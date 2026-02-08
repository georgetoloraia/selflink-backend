from __future__ import annotations

from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.db.models import Count, Exists, OuterRef, Value
from django.db.models.fields import BooleanField
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    AgreementAcceptance,
    ArtifactComment,
    Problem,
    ProblemAgreement,
    ProblemComment,
    ProblemCommentLike,
    ProblemLike,
    ProblemWork,
    WorkArtifact,
)
from .permissions import AgreementAcceptedForProblem
from .services.summary import get_community_summary
from .serializers import (
    ArtifactCommentSerializer,
    CommunityLoginSerializer,
    CommunityMeSerializer,
    CommunityLogoutSerializer,
    CommunityLoginResponseSerializer,
    CommunitySummarySerializer,
    ProblemAgreementSerializer,
    ProblemCommentSerializer,
    ProblemSerializer,
    ProblemWorkSerializer,
    UserTinySerializer,
    WorkArtifactSerializer,
)


class ProblemViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Problem.objects.filter(is_active=True).order_by("-created_at")
    serializer_class = ProblemSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):  # type: ignore[override]
        queryset = (
            Problem.objects.filter(is_active=True)
            .annotate(
                comments_count=Count("comments", distinct=True),
                artifacts_count=Count("artifacts", distinct=True),
                working_count=Count("work_entries", distinct=True),
                likes_count=Count("likes", distinct=True),
            )
            .order_by("-created_at")
        )
        user = getattr(self.request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            queryset = queryset.annotate(
                has_liked=Exists(
                    ProblemLike.objects.filter(problem=OuterRef("pk"), user=user)
                ),
                is_working=Exists(
                    ProblemWork.objects.filter(problem=OuterRef("pk"), user=user)
                ),
            )
        else:
            queryset = queryset.annotate(
                has_liked=Value(False, output_field=BooleanField()),
                is_working=Value(False, output_field=BooleanField()),
            )
        return queryset

    def get_permissions(self):  # type: ignore[override]
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        if self.action in {"work", "unwork", "artifacts", "comments", "like", "comment_like"} and self.request.method not in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated(), AgreementAcceptedForProblem()]
        if self.action == "agreement_accept":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def retrieve(self, request, *args, **kwargs) -> Response:
        instance = self.get_object()
        work_qs = (
            ProblemWork.objects.filter(problem=instance)
            .select_related("user")
            .only("user_id", "user__id", "user__handle", "user__photo")
        )
        working_users = [entry.user for entry in work_qs]
        serializer = self.get_serializer(
            instance,
            context={
                "request": request,
                "include_working_on_this": True,
                "working_users": working_users,
            },
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="agreement")
    def agreement(self, request, *args, **kwargs):
        problem = self.get_object()
        agreement = (
            ProblemAgreement.objects.filter(problem=problem, is_active=True)
            .only("id", "text", "is_active", "problem_id")
            .first()
        )
        payload = {
            "agreement": ProblemAgreementSerializer(agreement).data if agreement else None
        }
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="agreement/accept")
    def agreement_accept(self, request, *args, **kwargs):
        problem = self.get_object()
        agreement = (
            ProblemAgreement.objects.filter(problem=problem, is_active=True)
            .only("id", "problem_id")
            .first()
        )
        if not agreement:
            return Response({"detail": "AGREEMENT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
        AgreementAcceptance.objects.get_or_create(
            problem=problem,
            agreement=agreement,
            user=request.user,
        )
        return Response({"accepted": True, "agreement_id": agreement.id, "problem_id": problem.id})

    @action(detail=True, methods=["post"], url_path="work")
    def work(self, request, *args, **kwargs):
        problem = self.get_object()
        serializer = ProblemWorkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        work, created = ProblemWork.objects.update_or_create(
            problem=problem,
            user=request.user,
            defaults={
                "status": serializer.validated_data.get("status", "marked"),
                "note": serializer.validated_data.get("note", ""),
            },
        )
        working_count = ProblemWork.objects.filter(problem=problem).count()
        payload = {
            "working_count": working_count,
            "is_working": True,
            "problem_id": problem.id,
        }
        return Response(
            payload,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="work")
    def unwork(self, request, *args, **kwargs):
        problem = self.get_object()
        ProblemWork.objects.filter(problem=problem, user=request.user).delete()
        working_count = ProblemWork.objects.filter(problem=problem).count()
        return Response(
            {"working_count": working_count, "is_working": False, "problem_id": problem.id},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post", "delete"], url_path="like")
    def like(self, request, *args, **kwargs):
        problem = self.get_object()
        if request.method.lower() == "post":
            ProblemLike.objects.get_or_create(problem=problem, user=request.user)
            has_liked = True
        else:
            ProblemLike.objects.filter(problem=problem, user=request.user).delete()
            has_liked = False
        likes_count = ProblemLike.objects.filter(problem=problem).count()
        return Response(
            {"likes_count": likes_count, "has_liked": has_liked, "problem_id": problem.id},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post", "delete"], url_path=r"comments/(?P<comment_id>[^/.]+)/like")
    def comment_like(self, request, *args, **kwargs):
        problem = self.get_object()
        comment = get_object_or_404(ProblemComment, pk=kwargs.get("comment_id"), problem=problem)
        if request.method.lower() == "post":
            ProblemCommentLike.objects.get_or_create(comment=comment, user=request.user)
            has_liked = True
        else:
            ProblemCommentLike.objects.filter(comment=comment, user=request.user).delete()
            has_liked = False
        likes_count = ProblemCommentLike.objects.filter(comment=comment).count()
        return Response(
            {"likes_count": likes_count, "has_liked": has_liked, "comment_id": comment.id},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"], url_path="artifacts")
    def artifacts(self, request, *args, **kwargs):
        problem = self.get_object()
        if request.method.lower() == "get":
            queryset = WorkArtifact.objects.filter(problem=problem).order_by("-created_at")
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = WorkArtifactSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            serializer = WorkArtifactSerializer(queryset, many=True, context={"request": request})
            return Response(serializer.data)

        serializer = WorkArtifactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        artifact = WorkArtifact.objects.create(
            problem=problem,
            user=request.user,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            url=serializer.validated_data.get("url", ""),
        )
        return Response(
            WorkArtifactSerializer(artifact, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, *args, **kwargs):
        problem = self.get_object()
        if request.method.lower() == "get":
            queryset = (
                ProblemComment.objects.filter(problem=problem)
                .annotate(likes_count=Count("likes", distinct=True))
                .order_by("-created_at")
            )
            user = getattr(request, "user", None)
            if user and getattr(user, "is_authenticated", False):
                queryset = queryset.annotate(
                    has_liked=Exists(
                        ProblemCommentLike.objects.filter(comment=OuterRef("pk"), user=user)
                    )
                )
            else:
                queryset = queryset.annotate(
                    has_liked=Value(False, output_field=BooleanField())
                )
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ProblemCommentSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            serializer = ProblemCommentSerializer(queryset, many=True, context={"request": request})
            return Response(serializer.data)

        serializer = ProblemCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = ProblemComment.objects.create(
            problem=problem,
            user=request.user,
            body=serializer.validated_data["body"],
        )
        return Response(
            ProblemCommentSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ArtifactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkArtifact.objects.select_related("problem").order_by("-created_at")
    serializer_class = WorkArtifactSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):  # type: ignore[override]
        if self.action == "comments" and self.request.method not in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated(), AgreementAcceptedForProblem()]
        return [permissions.AllowAny()]

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, *args, **kwargs):
        artifact = self.get_object()
        if request.method.lower() == "get":
            queryset = ArtifactComment.objects.filter(artifact=artifact).order_by("-created_at")
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ArtifactCommentSerializer(page, many=True, context={"request": request})
                return self.get_paginated_response(serializer.data)
            serializer = ArtifactCommentSerializer(queryset, many=True, context={"request": request})
            return Response(serializer.data)

        serializer = ArtifactCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = ArtifactComment.objects.create(
            artifact=artifact,
            user=request.user,
            body=serializer.validated_data["body"],
        )
        return Response(
            ArtifactCommentSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CommunityLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs) -> Response:
        serializer = CommunityLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = authenticate(request=request, username=username, password=password)
        if not user:
            return Response({"detail": "INVALID_CREDENTIALS"}, status=status.HTTP_400_BAD_REQUEST)
        refresh = RefreshToken.for_user(user)
        payload = {
            "token_type": "Bearer",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserTinySerializer(user, context={"request": request}).data,
        }
        response_serializer = CommunityLoginResponseSerializer(payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class CommunityMeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs) -> Response:
        payload = {"user": UserTinySerializer(request.user, context={"request": request}).data}
        response_serializer = CommunityMeSerializer(payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class CommunityLogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs) -> Response:
        payload = {"ok": True}
        response_serializer = CommunityLogoutSerializer(payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class CommunitySummaryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs) -> Response:
        payload = get_community_summary()
        response_serializer = CommunitySummarySerializer(payload)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
