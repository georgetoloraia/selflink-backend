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

## Versioned Payload Guarantees (v1/v2)

**Core guarantees (all rules versions):**
- `user` object with fields: `id`, `handle`, `name`, `photo`
- `score` (int)
- `components` object with keys: `astro`, `matrix`, `psychology`, `lifestyle`
- `tags` (array of strings)

**Optional/best-effort enrichments (may be absent):**
- `lens`, `lens_label`, `lens_reason_short`
- `timing_score`, `timing_window`, `timing_summary`, `compatibility_trend`
- `explanation_level`, `explanation`

**/with/ async (202) guarantees:**
- `task_id`, `pair_key`, `rules_version`, `user` (same user fields as above)

**include_meta wrapper (recommendations):**
- When `include_meta=1`, response is `{results, meta}`
- `meta` includes: `mode`, `reason`, `missing_requirements`, `candidate_count`
- `candidate_count` currently equals `len(results)`
- `reason` is one of: `missing_birth_data`, `missing_profile_fields`, `no_candidates`, `no_results`, or `null`

**Change-control**
- Only fields documented above are guaranteed stable.
- In **200 OK** responses, keys beyond `user`, `user_id`, `score`, `components`, `tags` are produced by `calculate_soulmatch(...)` and may evolve; clients should treat them as stable only if documented.

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

### Debug counters (optional)

If `?debug_v2=1` is passed, meta also includes:

- `raw_candidate_count`
- `filtered_candidate_count`
- `returned_count`
- `invalid_counts` (missing_user_id, missing_score, etc.)

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
