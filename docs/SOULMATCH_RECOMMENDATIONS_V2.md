# SoulMatch Recommendations v2 (Backend)

This document describes the **additive** fields returned by `/api/v1/soulmatch/recommendations/` and how to use them for UI diversity, timing, and premium explanations.

## Lenses

Each recommendation includes:

- `lens` — one of:
  - `SOUL_RESONANCE`
  - `GROWTH_CATALYST`
  - `KARMIC_TIE`
  - `TIMING_MATCH`
  - `MIRROR_MATCH`
  - `OPPOSITE_POLARITY`
- `lens_label` — short UI label
- `lens_reason_short` — 1 sentence, deterministic heuristic

The list is diversified so no single lens dominates the top results.

## Timing fields

Each result includes:

- `timing_score` (0–100)
- `timing_window` (object or null)
- `timing_summary` (string)
- `compatibility_trend`: `improving | declining | stable | unknown`

MVP timing defaults to “unknown” unless a timing engine is added.

## Explanation levels (monetization-ready)

Use query param:
```
/api/v1/soulmatch/recommendations/?explain=free|premium|premium_plus
```

Each result includes:

- `explanation_level`
- `explanation`:
  - `short` (always)
  - `full` (premium+)
  - `strategy` (premium_plus)

## Empty reasons (meta)

If `include_meta=1`, response wraps:

```json
{
  "results": [...],
  "meta": {
    "missing_requirements": ["birth_date", "birth_time", "birth_place"],
    "reason": "missing_birth_data|no_candidates|no_results",
    "candidate_count": 42
  }
}
```

## Sample response (single item)

```json
{
  "user": { "id": 12, "handle": "alex", "name": "Alex", "photo": "..." },
  "score": 76,
  "components": { "astro": 25, "matrix": 15, "psychology": 20, "lifestyle": 16 },
  "tags": ["values_aligned"],
  "lens": "SOUL_RESONANCE",
  "lens_label": "Soul Resonance",
  "lens_reason_short": "High overall resonance across core dimensions.",
  "timing_score": 0,
  "timing_window": null,
  "timing_summary": "Timing unknown",
  "compatibility_trend": "unknown",
  "explanation_level": "free",
  "explanation": { "short": "High overall resonance across core dimensions." }
}
```
