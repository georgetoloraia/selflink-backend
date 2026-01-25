from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from apps.users.models import User


@dataclass
class TimingWindow:
    starts_at: str
    ends_at: str
    label: str


@dataclass
class TimingResult:
    timing_score: int
    timing_window: Optional[dict]
    timing_summary: str
    compatibility_trend: str


def evaluate_timing(user: User, candidate: User) -> TimingResult:
    """
    MVP timing evaluator. Returns 'unknown' unless a more reliable timing engine exists.
    """
    return TimingResult(
        timing_score=0,
        timing_window=None,
        timing_summary="Timing unknown",
        compatibility_trend="unknown",
    )
