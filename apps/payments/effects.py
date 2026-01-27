from __future__ import annotations

from typing import Any, Dict, List

from django.core.exceptions import ValidationError


_ALLOWED_EFFECT_TYPES = {"overlay", "border_glow", "highlight", "badge"}
_ALLOWED_SCOPES = {"post", "comment"}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float | None = None) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed


def _normalize_persist(persist: Any) -> Dict[str, Any]:
    if not isinstance(persist, dict):
        return {"mode": "none", "window_seconds": 0}
    mode = persist.get("mode")
    mode = "window" if mode == "window" else "none"
    window_seconds = _to_int(persist.get("window_seconds"), 0)
    return {
        "mode": mode,
        "window_seconds": max(window_seconds, 0),
    }


def _normalize_effect(effect: Dict[str, Any]) -> Dict[str, Any] | None:
    effect_type = effect.get("type")
    if effect_type not in _ALLOWED_EFFECT_TYPES:
        return None

    normalized: Dict[str, Any] = {"type": effect_type}
    scope = effect.get("scope")
    if isinstance(scope, str) and scope in _ALLOWED_SCOPES:
        normalized["scope"] = scope
    if "priority" in effect:
        normalized["priority"] = _to_int(effect.get("priority"), 0)

    if effect_type == "overlay":
        animation = effect.get("animation")
        if isinstance(animation, str) and animation.strip():
            normalized["animation"] = animation.strip()
        opacity = _to_float(effect.get("opacity"))
        if opacity is not None:
            normalized["opacity"] = opacity
        z_index = _to_int(effect.get("z_index"), 0)
        if z_index:
            normalized["z_index"] = z_index
        if "clip_to_bounds" in effect:
            normalized["clip_to_bounds"] = bool(effect.get("clip_to_bounds"))
        scale = _to_float(effect.get("scale"))
        if scale is not None:
            normalized["scale"] = scale
        if "loop" in effect:
            normalized["loop"] = bool(effect.get("loop"))
        fit = effect.get("fit")
        if fit in {"cover", "contain"}:
            normalized["fit"] = fit
        duration_ms = _to_int(effect.get("duration_ms"), 0)
        if duration_ms:
            normalized["duration_ms"] = duration_ms
    elif effect_type == "border_glow":
        color = effect.get("color")
        if isinstance(color, str) and color.strip():
            normalized["color"] = color.strip()
        thickness = _to_float(effect.get("thickness"))
        if thickness is not None:
            normalized["thickness"] = thickness
        intensity = _to_float(effect.get("intensity"))
        if intensity is not None:
            normalized["intensity"] = intensity
        if "pulse" in effect:
            normalized["pulse"] = bool(effect.get("pulse"))
    elif effect_type == "highlight":
        color = effect.get("color")
        if isinstance(color, str) and color.strip():
            normalized["color"] = color.strip()
        tone = effect.get("tone")
        if isinstance(tone, str) and tone.strip():
            normalized["tone"] = tone.strip()
    elif effect_type == "badge":
        text = effect.get("text")
        label = effect.get("label")
        if isinstance(text, str) and text.strip():
            normalized["text"] = text.strip()
        elif isinstance(label, str) and label.strip():
            normalized["label"] = label.strip()
        tone = effect.get("tone")
        if isinstance(tone, str) and tone.strip():
            normalized["tone"] = tone.strip()

    return normalized


def normalize_gift_effects(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    version = raw.get("version")
    version = version if isinstance(version, int) else 2
    effects_raw = raw.get("effects")
    effects_list: List[Dict[str, Any]] = []
    if isinstance(effects_raw, list):
        for item in effects_raw:
            if not isinstance(item, dict):
                continue
            normalized = _normalize_effect(item)
            if normalized is not None:
                effects_list.append(normalized)
    persist = _normalize_persist(raw.get("persist"))
    return {"version": version, "effects": effects_list, "persist": persist}


def validate_gift_effects(raw: Any) -> Dict[str, Any]:
    if raw is None or raw == "":
        return {"version": 2, "effects": [], "persist": {"mode": "none", "window_seconds": 0}}
    if not isinstance(raw, dict):
        raise ValidationError("effects must be an object")
    effects_raw = raw.get("effects")
    if effects_raw is not None and not isinstance(effects_raw, list):
        raise ValidationError("effects.effects must be a list")
    unknown_types = []
    if isinstance(effects_raw, list):
        for item in effects_raw:
            if not isinstance(item, dict):
                raise ValidationError("effects.effects entries must be objects")
            effect_type = item.get("type")
            if effect_type not in _ALLOWED_EFFECT_TYPES:
                if effect_type:
                    unknown_types.append(effect_type)
                else:
                    unknown_types.append("<missing>")
            if effect_type == "overlay":
                animation = item.get("animation")
                if not isinstance(animation, str) or not animation.strip():
                    raise ValidationError("overlay effects require a non-empty animation")
    if unknown_types:
        raise ValidationError(f"Unsupported effect type(s): {', '.join(unknown_types)}")
    return normalize_gift_effects(raw)
