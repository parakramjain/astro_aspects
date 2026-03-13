from __future__ import annotations

import re
from typing import Dict, List


class DeterministicReportParser:
    def __init__(self, driver_map: Dict, taxonomy: Dict | None = None):
        self.driver_map = driver_map or {}
        self.taxonomy = taxonomy or {}
        self._taxonomy_by_label = {
            str(row.get("driver_label", "")).strip(): row
            for row in self.taxonomy.get("driver_taxonomy", [])
            if str(row.get("driver_label", "")).strip()
        }

    def extract_drivers(self, text: str) -> List[Dict[str, str]]:
        normalized = (text or "").lower()
        hits: List[Dict[str, str]] = []
        for driver in self.driver_map.get("drivers", []):
            label = driver.get("label", "")
            patterns = driver.get("patterns", [])
            for pattern in patterns:
                if re.search(rf"\b{re.escape(pattern.lower())}\b", normalized):
                    meta = self._taxonomy_by_label.get(label, {})
                    hits.append(
                        {
                            "driver_label": label,
                            "driver_category": str(meta.get("driver_category", "Execution")),
                            "polarity": str(meta.get("polarity", "positive")),
                            "matched_pattern": str(pattern),
                        }
                    )
                    break

        uniq: Dict[str, Dict[str, str]] = {}
        for row in hits:
            key = row["driver_label"]
            if key not in uniq:
                uniq[key] = row
        return [uniq[key] for key in sorted(uniq.keys())]

    def evidence_snippet(self, text: str, pattern: str, max_chars: int = 120) -> str:
        source = (text or "").strip()
        if not source:
            return ""
        try:
            found = re.search(rf"\b{re.escape(pattern)}\b", source, flags=re.IGNORECASE)
        except re.error:
            found = None
        if not found:
            return source[:max_chars].strip()
        start = max(0, found.start() - 40)
        end = min(len(source), found.end() + 60)
        snippet = source[start:end].strip()
        return snippet[:max_chars].strip()

    def fallback_driver(self, effect: str) -> str:
        return self.driver_map.get("fallback", {}).get(effect, "Baseline progress")

    def fallback_driver_meta(self, effect: str) -> Dict[str, str]:
        fallback = self.taxonomy.get("fallback", {}).get(effect, {})
        return {
            "driver_label": str(fallback.get("driver_label", "Baseline progress")),
            "driver_category": str(fallback.get("driver_category", "Execution")),
            "polarity": str(fallback.get("polarity", "positive" if effect == "positive" else "negative")),
            "matched_pattern": "fallback",
        }
