from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.astro.models import NatalChart
from apps.astro.serializers import BirthDataSerializer, NatalChartSerializer
from apps.astro.services import birthdata_service, chart_calculator, ephemeris
from apps.astro.services.location_resolver import LocationResolutionError

logger = logging.getLogger(__name__)


class NatalChartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request) -> Response:
        user = request.user
        if request.data.get("source") == "profile":
            try:
                birth_data = birthdata_service.create_or_update_birth_data_from_profile(user)
            except birthdata_service.BirthDataIncompleteError:
                return Response(
                    {
                        "detail": "No complete birth data stored in profile. Please provide or correct your birth information."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except LocationResolutionError:
                return Response(
                    {
                        "detail": "Unable to resolve location for your birth place. Please update your city and country or contact support."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            created = not hasattr(user, "birth_data")
        else:
            serializer = BirthDataSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            created = not hasattr(user, "birth_data")
            birth_data = serializer.save()

        try:
            chart = chart_calculator.calculate_natal_chart(birth_data)
        except ephemeris.AstroCalculationError as exc:
            logger.exception("Natal chart calculation failed", extra={"user_id": user.id})
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        chart_serializer = NatalChartSerializer(chart)
        return Response(chart_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MyNatalChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request) -> Response:
        user = request.user
        try:
            chart = NatalChart.objects.get(user=user)
        except NatalChart.DoesNotExist:
            return Response(
                {"detail": "No natal chart found. Submit birth data to generate one."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = NatalChartSerializer(chart)
        return Response(serializer.data)
