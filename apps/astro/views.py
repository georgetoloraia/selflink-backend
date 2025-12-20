from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.astro.cache import get_cached_or_compute
from apps.astro.models import BirthData, NatalChart
from apps.astro.serializers import BirthDataSerializer, NatalChartSerializer
from apps.astro.services import birthdata_service, chart_calculator, ephemeris
from apps.astro.tasks import astrology_compute_birth_chart_task
from apps.astro.services.location_resolver import LocationResolutionError
from apps.core_platform.async_mode import should_run_async

logger = logging.getLogger(__name__)


class NatalChartView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "astro"

    def post(self, request) -> Response:
        user = request.user
        had_birth_data = BirthData.objects.filter(user=user).exists()
        payload_fields = {
            "date_of_birth",
            "time_of_birth",
            "timezone",
            "city",
            "country",
            "latitude",
            "longitude",
        }
        use_profile_source = request.data.get("source") == "profile" and not any(
            field in request.data for field in payload_fields
        )

        if use_profile_source:
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
            except Exception:
                logger.exception("Birth data resolution failed", extra={"user_id": user.id})
                return Response(
                    {
                        "detail": "Unable to resolve location for your birth place. Please update your city and country or contact support."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            created = not had_birth_data
        else:
            serializer = BirthDataSerializer(data=request.data, context={"request": request})
            serializer.is_valid(raise_exception=True)
            birth_data = serializer.save()
            created = serializer.context.get("created", not had_birth_data)

        if should_run_async(request):
            task_result = astrology_compute_birth_chart_task.apply_async(args=[birth_data.id])
            return Response(
                {
                    "birth_data_id": birth_data.id,
                    "task_id": task_result.id,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        try:
            _, chart = get_cached_or_compute(birth_data, calculate_fn=chart_calculator.calculate_natal_chart)
        except ephemeris.AstroCalculationError as exc:
            logger.exception("Natal chart calculation failed", extra={"user_id": user.id})
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        chart_serializer = NatalChartSerializer(chart)
        return Response(chart_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MyNatalChartView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "astro"

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
