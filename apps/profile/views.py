from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profile.models import UserProfile
from apps.profile.serializers import UserProfileSerializer


class MeProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            # Return an empty/default profile payload so clients can render/edit immediately.
            profile = UserProfile(user=user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        try:
            profile = user.profile
            was_empty = profile.is_empty()
            serializer = UserProfileSerializer(profile, data=request.data, partial=True, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            status_code = status.HTTP_201_CREATED if was_empty else status.HTTP_200_OK
        except UserProfile.DoesNotExist:
            serializer = UserProfileSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            profile = serializer.save()
            status_code = status.HTTP_201_CREATED

        return Response(UserProfileSerializer(profile).data, status=status_code)
