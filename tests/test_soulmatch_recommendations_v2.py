from __future__ import annotations

from apps.matching.services.recommendations_v2 import assign_lens, diversify


def test_assign_lens_timing_match() -> None:
    lens, label, reason = assign_lens(
        score=60,
        components={"astro": 10, "psychology": 10, "lifestyle": 5},
        tags=["neutral"],
        timing_score=80,
    )
    assert lens == "TIMING_MATCH"
    assert label
    assert reason


def test_diversify_caps_dominant_lens() -> None:
    items = []
    for idx in range(10):
        items.append({"lens": "SOUL_RESONANCE", "score": 90 - idx, "_rank_score": 90 - idx})
    items.append({"lens": "GROWTH_CATALYST", "score": 50, "_rank_score": 50})

    results = diversify(items, limit=10)
    lens_counts = {}
    for item in results:
        lens_counts[item["lens"]] = lens_counts.get(item["lens"], 0) + 1
    assert lens_counts.get("SOUL_RESONANCE", 0) <= 4  # 40% of 10
    assert lens_counts.get("GROWTH_CATALYST", 0) >= 1
