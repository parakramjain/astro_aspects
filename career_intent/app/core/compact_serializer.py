from __future__ import annotations

import datetime as dt
import re
from typing import Any, Dict, List


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _clip_text(text: str, max_len: int) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if len(clean) <= max_len:
        return clean
    return clean[:max_len].rstrip()


class CompactSerializer:
    UNSAFE = ["firearms", "firearm", "explosives", "explosive", "weapon", "weapons"]
    CATEGORY_CATALOG = {
        "g": "growth",
        "e": "execution",
        "s": "stability",
        "p": "pressure",
        "l": "learning",
        "o": "opportunity",
    }

    def __init__(self, *, thresholds: Dict[str, Any], driver_map: Dict[str, Any], driver_catalog: Dict[str, Any]):
        compact_cfg = thresholds.get("compact", {}) if isinstance(thresholds, dict) else {}
        self.top_intents = _safe_int(compact_cfg.get("top_intents", 3), 3)
        self.top_aspects = _safe_int(compact_cfg.get("top_aspects", 10), 10)
        self.min_aspect_days = _safe_int(compact_cfg.get("min_aspect_days", 3), 3)
        self.keep_high_impact_threshold = _safe_int(compact_cfg.get("keep_high_impact_threshold", 70), 70)
        self.max_desc_len = min(90, _safe_int(compact_cfg.get("max_desc_len", 90), 90))

        catalog = driver_catalog.get("catalog", {}) if isinstance(driver_catalog, dict) else {}
        self.driver_catalog: Dict[str, str] = {}
        for key, value in sorted(catalog.items(), key=lambda item: str(item[0])):
            raw_key = str(key).strip()
            label = str(value).strip()
            if not raw_key or not label:
                continue
            driver_id = raw_key if raw_key.startswith("drv_") else f"drv_{_norm(raw_key)}"
            self.driver_catalog[driver_id] = label

        if not self.driver_catalog:
            for row in (driver_map.get("drivers", []) if isinstance(driver_map, dict) else []):
                key = str(row.get("key", "")).strip()
                label = str(row.get("label", "")).strip()
                if key and label:
                    driver_id = key if key.startswith("drv_") else f"drv_{_norm(key)}"
                    self.driver_catalog[driver_id] = label

        fallback = driver_map.get("fallback", {}) if isinstance(driver_map, dict) else {}
        for label in [fallback.get("opportunity"), fallback.get("risk")]:
            text = str(label or "").strip()
            if not text:
                continue
            fallback_id = f"drv_{_norm(text)}"
            self.driver_catalog.setdefault(fallback_id, text)

        self.label_to_id: Dict[str, str] = {}
        for driver_id, label in self.driver_catalog.items():
            self.label_to_id[_norm(label)] = driver_id
            self.label_to_id[_norm(driver_id)] = driver_id

    def get_driver_catalog(self) -> Dict[str, str]:
        return dict(sorted(self.driver_catalog.items(), key=lambda item: item[0]))

    def get_category_catalog(self) -> Dict[str, str]:
        return dict(self.CATEGORY_CATALOG)

    def _driver_ids(self, labels: List[str]) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()
        for raw in labels:
            label = str(raw or "").strip()
            if not label:
                continue
            lookup = self.label_to_id.get(_norm(label))
            if lookup:
                driver_id = lookup
            else:
                driver_id = f"drv_{_norm(label)[:24]}" if _norm(label) else "drv_unknown"
            if driver_id in seen:
                continue
            seen.add(driver_id)
            out.append(driver_id)
        return out

    def _duration_days(self, start_iso: str, end_iso: str) -> int:
        try:
            start = dt.date.fromisoformat(str(start_iso)[:10])
            end = dt.date.fromisoformat(str(end_iso)[:10])
            return (end - start).days + 1 if end >= start else 0
        except Exception:
            return 0

    def _sanitize_text(self, text: str) -> str:
        out = str(text or "")
        for token in self.UNSAFE:
            out = re.sub(rf"\b{re.escape(token)}\b", "hazardous tools/activities", out, flags=re.IGNORECASE)
        return " ".join(out.split()).strip()

    def _single_sentence(self, text: str) -> str:
        cleaned = self._sanitize_text(text)
        if not cleaned:
            return ""
        parts = re.split(r"[.!?]+", cleaned)
        sentence = parts[0].strip()
        if not sentence:
            sentence = cleaned[: self.max_desc_len].strip()
        return sentence + "."

    def _aspect_category(self, aspect_name: str, description: str) -> str:
        text = f"{aspect_name} {description}".lower()
        if any(x in text for x in ["learn", "skill", "training"]):
            return "l"
        if any(x in text for x in ["pressure", "delay", "stress", "risk", "square", "opposition"]):
            return "p"
        if any(x in text for x in ["stability", "structure", "steady"]):
            return "s"
        if any(x in text for x in ["execute", "delivery", "momentum"]):
            return "e"
        if any(x in text for x in ["trine", "sextile", "growth", "expand"]):
            return "g"
        return "o"

    def _aspect_summary(self, aspect_name: str, description: str, impact_score: int) -> str:
        category = self._aspect_category(aspect_name, description)
        if category == "g":
            base = "Supports growth through focused execution and consistent follow-through."
        elif category == "e":
            base = "Prioritize execution sequencing and measurable weekly delivery checkpoints."
        elif category == "s":
            base = "Stability improves with structured planning and disciplined pacing."
        elif category == "p":
            base = "Manage pressure with tighter scope and risk-controlled decisions."
        elif category == "l":
            base = "Learning gains improve when effort is consistent and outcomes are tracked."
        else:
            base = "Use this window for practical opportunity moves with clear priorities."

        if impact_score >= 75:
            base = "High-impact phase; act decisively with clear scope and accountability."
        elif impact_score <= 35:
            base = "Low-intensity phase; focus on maintenance and preparation."

        sentence = self._single_sentence(base)
        sentence = sentence.replace("…", "").strip()
        return _clip_text(sentence, self.max_desc_len)

    def serialize(self, insight: Dict[str, Any], *, config_version: str = "0.1.0") -> Dict[str, Any]:
        meta = insight.get("metadata", {})
        score = insight.get("score_breakdown", {})
        ow = insight.get("opportunity_window", {})
        cw = insight.get("caution_window", {})
        action_plan = insight.get("action_plan", {})

        intents = []
        for row in insight.get("career_intent_scores", []):
            window = str(row.get("recommended_window", "neutral")).lower()
            mapped_w = "o" if window.startswith("opp") else ("c" if window.startswith("cau") else "n")
            intents.append(
                {
                    "n": str(row.get("intent_name", "")).strip(),
                    "sc": _safe_int(row.get("score", 0)),
                    "w": mapped_w,
                    "ns": _clip_text(self._sanitize_text(str(row.get("next_step", "")).strip()), 90),
                }
            )
        intents.sort(key=lambda row: (-row["sc"], row["n"]))
        intents = intents[: max(1, self.top_intents)]

        aspects = []
        for row in insight.get("astro_aspects", []):
            start_iso = str(row.get("start_date", ""))[:10]
            end_iso = str(row.get("end_date", ""))[:10]
            exact_iso = str(row.get("exact_date", ""))[:10] or start_iso
            impact = _safe_int(row.get("impact_score", 0))
            if self._duration_days(start_iso, end_iso) < self.min_aspect_days and impact < self.keep_high_impact_threshold:
                continue
            aspect_name = str(row.get("aspect_name", "")).strip()
            summary = self._aspect_summary(aspect_name, str(row.get("description", "")), impact)
            aspects.append(
                {
                    "n": aspect_name,
                    "s": start_iso,
                    "e": end_iso,
                    "x": exact_iso,
                    "sc": impact,
                    "c": self._aspect_category(aspect_name, str(row.get("description", ""))),
                    "ds": summary,
                }
            )

        aspects.sort(key=lambda row: (-row["sc"], row["s"], row["n"]))
        aspects = aspects[: max(0, self.top_aspects)]

        pre = [_clip_text(self._sanitize_text(str(x)), 90) for x in action_plan.get("now_to_opportunity_start", []) if str(x).strip()]
        opp = [_clip_text(self._sanitize_text(str(x)), 90) for x in action_plan.get("during_opportunity", []) if str(x).strip()]
        cau = [_clip_text(self._sanitize_text(str(x)), 90) for x in action_plan.get("during_caution", []) if str(x).strip()]

        compact = {
            "v": str(config_version),
            "tf": {"s": str(meta.get("timeframe_start", ""))[:10], "e": str(meta.get("timeframe_end", ""))[:10]},
            "cms": _safe_int(insight.get("career_momentum_score", 0)),
            "sd": {
                "t": _safe_int(score.get("timing_strength", 0)),
                "st": _safe_int(score.get("execution_stability", 0)),
                "r": _safe_int(score.get("risk_pressure", 0)),
                "g": _safe_int(score.get("growth_leverage", 0)),
            },
            "ow": {
                "s": str(ow.get("start_date", ""))[:10],
                "e": str(ow.get("end_date", ""))[:10],
                "sc": _safe_int(ow.get("score", 0)),
                "d": self._driver_ids([str(x) for x in (ow.get("top_drivers") or [])]),
            },
            "cw": {
                "s": str(cw.get("start_date", ""))[:10],
                "e": str(cw.get("end_date", ""))[:10],
                "sc": _safe_int(cw.get("score", 0)),
                "d": self._driver_ids([str(x) for x in (cw.get("top_drivers") or [])]),
            },
            "ti": intents,
            "ap": {"pre": pre, "opp": opp, "cau": cau},
            "ax": aspects,
            "md": {
                "id": str(meta.get("request_id", "")),
                "h": str(meta.get("deterministic_hash", "")),
                "ff": sorted({str(x) for x in meta.get("fallback_flags", []) if str(x).strip()}),
            },
        }
        return compact
