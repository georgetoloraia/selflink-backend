from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AstroProfile, MatrixData
from .serializers import AstroProfileSerializer, MatrixDataSerializer, MatrixSyncSerializer
from .services import compute_life_path


class MatrixProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        astro, _ = AstroProfile.objects.get_or_create(user=request.user)
        matrix, _ = MatrixData.objects.get_or_create(user=request.user)
        if not matrix.life_path and request.user.birth_date:
            life_path, traits = compute_life_path(request.user.birth_date)
            matrix.life_path = life_path
            matrix.traits = traits
            matrix.save()
        data = {
            "astro": AstroProfileSerializer(astro).data,
            "matrix": MatrixDataSerializer(matrix).data,
        }
        return Response(data)


class MatrixSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = MatrixSyncSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        matrix = serializer.save()
        return Response(MatrixDataSerializer(matrix).data, status=status.HTTP_200_OK)
