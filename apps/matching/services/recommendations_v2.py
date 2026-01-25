from __future__ import annotations

from typing import Dict, List, Tuple


LENSES = [
    "SOUL_RESONANCE",
    "GROWTH_CATALYST",
    "KARMIC_TIE",
    "TIMING_MATCH",
    "MIRROR_MATCH",
    "OPPOSITE_POLARITY",
]

LENS_LABELS = {
    "SOUL_RESONANCE": "Soul Resonance",
    "GROWTH_CATALYST": "Growth Catalyst",
    "KARMIC_TIE": "Karmic Tie",
    "TIMING_MATCH": "Timing Match",
    "MIRROR_MATCH": "Mirror Match",
    "OPPOSITE_POLARITY": "Opposite Polarity",
}

LENS_REASONS = {
    "SOUL_RESONANCE": "High overall resonance across core dimensions.",
    "GROWTH_CATALYST": "Strong potential with challenges that can drive growth.",
    "KARMIC_TIE": "Rare high-intensity resonance signal in your overlap.",
    "TIMING_MATCH": "This connection looks timely in the near term.",
    "MIRROR_MATCH": "Shared values and lifestyle signals suggest a mirror match.",
    "OPPOSITE_POLARITY": "Complementary traits suggest an opposites-attract dynamic.",
}


def assign_lens(score: int, components: Dict[str, float], tags: List[str], timing_score: int) -> Tuple[str, str, str]:
    if timing_score >= 70:
        lens = "TIMING_MATCH"
    elif "soulmate_like" in tags and score >= 85:
        lens = "KARMIC_TIE"
    elif score >= 75 and ("values_aligned" in tags or "soulmate_like" in tags):
        lens = "SOUL_RESONANCE"
    elif "growth_opportunity" in tags or "strong_chemistry_needs_work" in tags:
        lens = "GROWTH_CATALYST"
    elif components.get("psychology", 0) >= 12 and components.get("lifestyle", 0) >= 7:
        lens = "MIRROR_MATCH"
    elif components.get("astro", 0) <= 20 and components.get("psychology", 0) <= 8:
        lens = "OPPOSITE_POLARITY"
    else:
        lens = "SOUL_RESONANCE"
    return lens, LENS_LABELS[lens], LENS_REASONS[lens]


def explanation_for(lens: str, level: str) -> Dict[str, str]:
    short = LENS_REASONS.get(lens, "Compatibility insight available.")
    data = {"short": short}
    if level in {"premium", "premium_plus"}:
        data["full"] = f"{short} Consider this as a strong starting signal."
    if level == "premium_plus":
        data["strategy"] = "Lead with curiosity and reflect on shared values before deep commitment."
    return data


def diversify(recommendations: List[dict], limit: int) -> List[dict]:
    if not recommendations:
        return []
    max_per_lens = max(1, int(limit * 0.4))
    buckets: Dict[str, List[dict]] = {lens: [] for lens in LENSES}
    for item in recommendations:
        lens = item.get("lens") or "SOUL_RESONANCE"
        buckets.setdefault(lens, []).append(item)
    for lens_items in buckets.values():
        lens_items.sort(key=lambda row: row.get("_rank_score", row.get("score", 0)), reverse=True)

    lens_order = [lens for lens in LENSES if buckets.get(lens)]
    counts = {lens: 0 for lens in lens_order}
    output: List[dict] = []
    while len(output) < limit:
        progressed = False
        for lens in lens_order:
            if counts[lens] >= max_per_lens:
                continue
            items = buckets.get(lens, [])
            if not items:
                continue
            output.append(items.pop(0))
            counts[lens] += 1
            progressed = True
            if len(output) >= limit:
                break
        if not progressed:
            break
    if len(output) < limit:
        remaining = [item for items in buckets.values() for item in items]
        remaining.sort(key=lambda row: row.get("_rank_score", row.get("score", 0)), reverse=True)
        output.extend(remaining[: limit - len(output)])
    return output[:limit]
