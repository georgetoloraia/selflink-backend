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
from apps.users.models import Block, Mute, User
from apps.profile.models import UserProfile

logger = logging.getLogger(__name__)


def _get_profile(user: User) -> UserProfile | None:
    profile = UserProfile.objects.filter(user_id=user.id).first()
    if profile and profile.is_empty():
        return None
    return profile


def _get_location_value(user: User, profile: UserProfile | None) -> str | None:
    if user.birth_place:
        return user.birth_place
    if profile and profile.birth_city:
        return profile.birth_city
    if profile and profile.birth_country:
        return profile.birth_country
    return None


def _missing_profile_requirements(user: User) -> list[str]:
    profile = _get_profile(user)
    missing: list[str] = []
    if not profile or not profile.gender:
        missing.append("gender")
    if not profile or not profile.orientation:
        missing.append("orientation")
    if not _get_location_value(user, profile):
        missing.append("location")
    return missing


def _build_candidate_queryset(current_user: User):
    queryset = User.objects.exclude(id=current_user.id).filter(is_active=True)
    blocked_ids = Block.objects.filter(user=current_user).values_list("target_id", flat=True)
    muted_ids = Mute.objects.filter(user=current_user).values_list("target_id", flat=True)
    if blocked_ids:
        queryset = queryset.exclude(id__in=blocked_ids)
    if muted_ids:
        queryset = queryset.exclude(id__in=muted_ids)
    return queryset


class SoulmatchWithView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "matching"

    def get(self, request, user_id: int):
        current_user: User = request.user
        mode = request.query_params.get("mode") or "compat"
        if mode not in {"compat", "dating"}:
            mode = "compat"
        include_meta = request.query_params.get("include_meta") in {"1", "true", "yes"}
        if current_user.id == user_id:
            return Response({"detail": "Cannot compute SoulMatch with yourself."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if mode == "dating":
            if not target.is_active:
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            if Block.objects.filter(user=current_user, target=target).exists():
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            if Mute.objects.filter(user=current_user, target=target).exists():
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
        if include_meta:
            missing_requirements: list[str] = []
            if not current_user.birth_date:
                missing_requirements.append("birth_date")
            if not current_user.birth_time:
                missing_requirements.append("birth_time")
            if not current_user.birth_place:
                missing_requirements.append("birth_place")
            if mode == "dating":
                missing_requirements.extend(_missing_profile_requirements(current_user))
            payload["meta"] = {
                "mode": mode,
                "eligibility": {
                    "eligible": not missing_requirements,
                    "missing_requirements": missing_requirements,
                },
            }
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
        mode = request.query_params.get("mode") or "compat"
        if mode not in {"compat", "dating"}:
            mode = "compat"
        debug_v2 = request.query_params.get("debug_v2") in {"1", "true", "yes"}
        candidate_queryset = _build_candidate_queryset(current_user).order_by("id")
        candidates = list(candidate_queryset[:50])
        candidate_count = len(candidates)
        random.shuffle(candidates)

        recommendations = []
        following_ids = get_following_ids(current_user)
        missing_profile_requirements = _missing_profile_requirements(current_user) if mode == "dating" else []
        invalid_counts = {
            "missing_user": 0,
            "missing_user_id": 0,
            "missing_score": 0,
        }
        for candidate in candidates:
            if mode == "dating":
                candidate_profile = _get_profile(candidate)
                if not candidate_profile or not candidate_profile.gender or not candidate_profile.orientation:
                    continue
                if not _get_location_value(candidate, candidate_profile):
                    continue
            # TODO: batch this via Celery if we keep computing many matches per request.
            result = calculate_soulmatch(current_user, candidate)
            if not candidate or not candidate.id:
                invalid_counts["missing_user_id"] += 1
                continue
            if result is None or result.get("score") is None:
                invalid_counts["missing_score"] += 1
                continue
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

        recommendations.sort(key=lambda item: (item["_rank_score"], item["user"]["id"]), reverse=True)
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
            if mode == "dating":
                missing_requirements.extend(missing_profile_requirements)

            reason = None
            if missing_requirements and any(item in {"birth_date", "birth_time", "birth_place"} for item in missing_requirements):
                reason = "missing_birth_data"
            elif mode == "dating" and missing_profile_requirements:
                reason = "missing_profile_fields"
            elif candidate_count == 0:
                reason = "no_candidates"
            elif len(data) == 0:
                reason = "no_results"

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

            meta = {
                "missing_requirements": missing_requirements,
                "reason": reason,
                "candidate_count": len(data),
                "mode": mode,
            }
            if debug_v2:
                meta.update(
                    {
                        "raw_candidate_count": candidate_count,
                        "filtered_candidate_count": len(recommendations),
                        "returned_count": len(data),
                        "invalid_counts": invalid_counts,
                    }
                )
            return Response(
                {
                    "results": data,
                    "meta": meta,
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
