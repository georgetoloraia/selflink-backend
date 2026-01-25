from __future__ import annotations

import random

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.matching.serializers import SoulmatchResultSerializer, SoulmatchUserSerializer
from apps.matching.services.personalization import get_following_ids, personalization_adjustment
from apps.matching.services.recommendations_v2 import assign_lens, diversify, explanation_for
from apps.matching.services.timing import evaluate_timing
from apps.matching.services.soulmatch import calculate_soulmatch
from apps.matching.tasks import soulmatch_compute_score_task
from apps.core_platform.async_mode import should_run_async
from apps.users.models import User

logger = logging.getLogger(__name__)


class SoulmatchWithView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "matching"

    def get(self, request, user_id: int):
        current_user: User = request.user
        if current_user.id == user_id:
            return Response({"detail": "Cannot compute SoulMatch with yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if should_run_async(request):
            pair_key = f"{min(current_user.id, target.id)}:{max(current_user.id, target.id)}"
            rules_version = getattr(settings, "MATCH_RULES_VERSION", "v1")
            task_result = soulmatch_compute_score_task.apply_async(
                args=[current_user.id, target.id],
                kwargs={"rules_version": rules_version},
            )
            return Response(
                {
                    "task_id": task_result.id,
                    "pair_key": pair_key,
                    "rules_version": rules_version,
                    "user": SoulmatchUserSerializer(target).data,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        result = calculate_soulmatch(current_user, target)
        payload = {"user": SoulmatchUserSerializer(target).data, **result}
        return Response(payload, status=status.HTTP_200_OK)


class SoulmatchRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "matching"

    def get(self, request):
        current_user: User = request.user
        include_meta = request.query_params.get("include_meta") in {"1", "true", "yes"}
        explain_level = request.query_params.get("explain") or "free"
        if explain_level not in {"free", "premium", "premium_plus"}:
            explain_level = "free"
        candidates = list(User.objects.exclude(id=current_user.id).order_by("id")[:50])
        candidate_count = len(candidates)
        random.shuffle(candidates)

        recommendations = []
        following_ids = get_following_ids(current_user)
        for candidate in candidates:
            # TODO: batch this via Celery if we keep computing many matches per request.
            result = calculate_soulmatch(current_user, candidate)
            timing = evaluate_timing(current_user, candidate)
            lens, lens_label, lens_reason_short = assign_lens(
                result["score"],
                result.get("components", {}),
                result.get("tags", []),
                timing.timing_score,
            )
            personalization = personalization_adjustment(current_user, candidate, following_ids)
            rank_score = result["score"] + personalization + (timing.timing_score / 20.0)
            payload = {
                "user": SoulmatchUserSerializer(candidate).data,
                **result,
                "lens": lens,
                "lens_label": lens_label,
                "lens_reason_short": lens_reason_short,
                "timing_score": timing.timing_score,
                "timing_window": timing.timing_window,
                "timing_summary": timing.timing_summary,
                "compatibility_trend": timing.compatibility_trend,
                "explanation_level": explain_level,
                "explanation": explanation_for(lens, explain_level),
                "_rank_score": rank_score,
            }
            recommendations.append(payload)

        recommendations.sort(key=lambda item: item["_rank_score"], reverse=True)
        diversified = diversify(recommendations, limit=20)
        for item in diversified:
            item.pop("_rank_score", None)
        serializer = SoulmatchResultSerializer(diversified, many=True)
        data = serializer.data

        if include_meta:
            missing_requirements = []
            if not current_user.birth_date:
                missing_requirements.append("birth_date")
            if not current_user.birth_time:
                missing_requirements.append("birth_time")
            if not current_user.birth_place:
                missing_requirements.append("birth_place")

            reason = None
            if candidate_count == 0:
                reason = "no_candidates"
            elif len(data) == 0:
                reason = "no_results"
            elif missing_requirements:
                reason = "missing_birth_data"

            if settings.DEBUG:
                logger.debug(
                    "Soulmatch recommendations meta",
                    extra={
                        "user_id": current_user.id,
                        "candidate_count": candidate_count,
                        "result_count": len(data),
                        "missing_requirements": missing_requirements,
                        "reason": reason,
                    },
                )

            return Response(
                {
                    "results": data,
                    "meta": {
                        "missing_requirements": missing_requirements,
                        "reason": reason,
                        "candidate_count": candidate_count,
                    },
                },
                status=status.HTTP_200_OK,
            )

        if settings.DEBUG:
            logger.debug(
                "Soulmatch recommendations",
                extra={
                    "user_id": current_user.id,
                    "candidate_count": candidate_count,
                    "result_count": len(data),
                },
            )

        return Response(data, status=status.HTTP_200_OK)
