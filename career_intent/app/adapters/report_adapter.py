from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from schemas import TimelineRequest


@dataclass
class ReportAdapterResult:
    items: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
    fallback_flags: List[str] = field(default_factory=list)


class ReportServiceAdapter:
    def _period_for_months(self, months: int) -> str:
        if months >= 12:
            return "1Y"
        if months >= 6:
            return "6M"
        return "1M"

    def fetch(
        self,
        birth_payload: Dict[str, Any],
        start_date: dt.date,
        end_date: dt.date,
        months: int,
    ) -> ReportAdapterResult:
        out = ReportAdapterResult()
        try:
            from services.report_services import compute_timeline

            req = TimelineRequest(
                **birth_payload,
                timePeriod=self._period_for_months(months),
                reportStartDate=start_date.isoformat(),
                cursor=None,
            )
            timeline = compute_timeline(req)
            data = timeline.model_dump() if hasattr(timeline, "model_dump") else timeline.dict()
            items = data.get("items", [])
            filtered: List[Dict[str, Any]] = []
            for item in items:
                end_iso = str(item.get("endDate", ""))[:10]
                if end_iso and end_iso < start_date.isoformat():
                    continue
                start_iso = str(item.get("startDate", ""))[:10]
                if start_iso and start_iso > end_date.isoformat():
                    continue
                filtered.append(item)
            out.items = filtered
        except Exception:
            out.fallback_flags.append("report_adapter_fallback")
        if not out.items:
            out.raw_text = ""
        return out
