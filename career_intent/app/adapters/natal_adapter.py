from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from schemas import BirthPayload


@dataclass
class NatalAdapterResult:
    chart: Dict[str, Any] = field(default_factory=dict)
    aspects: List[Dict[str, Any]] = field(default_factory=list)
    fallback_flags: List[str] = field(default_factory=list)


class NatalServiceAdapter:
    def compute(self, payload: Dict[str, Any]) -> NatalAdapterResult:
        result = NatalAdapterResult()
        try:
            from services.natal_services import calculate_natal_chart_data, compute_natal_natal_aspects

            model = BirthPayload(**payload)
            chart_data = calculate_natal_chart_data(model)
            aspects_data = compute_natal_natal_aspects(model)
            result.chart = chart_data.model_dump() if hasattr(chart_data, "model_dump") else chart_data.dict()
            result.aspects = [item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in aspects_data]
        except Exception:
            result.fallback_flags.append("natal_adapter_fallback")
        return result
