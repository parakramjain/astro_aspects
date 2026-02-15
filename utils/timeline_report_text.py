from __future__ import annotations
import datetime as dt
from typing import List, Optional, Dict, Any
import ast
import pytz

def _format_date(val: Any) -> str:
    if isinstance(val, dt.datetime):
        return val.date().isoformat()
    if isinstance(val, dt.date):
        return val.isoformat()
    if isinstance(val, str):
        try:
            return dt.datetime.fromisoformat(val).date().isoformat()
        except ValueError:
            return val[:10] if len(val) >= 10 else val
    return ""

def timeline_report_text(timeline_output: Any, lang_code: str = "en") -> str:
    doc_lines: List[str] = []
    sorted_items = sorted(
        timeline_output.items,
        key=lambda x: (
            _format_date(getattr(x, "startDate", "")),
            _format_date(getattr(x, "exactDate", "")),
            str(getattr(x, "aspect", "")),
        ),
        reverse=False,
    )
    for item in sorted_items:
        # print(item.aspect, item.aspectNature, item.startDate, item.exactDate, item.endDate)
        start_date = _format_date(item.startDate)
        end_date = _format_date(item.endDate)
        exact_date = _format_date(item.exactDate)
        nature = str(item.aspectNature).lower()
        color = "green" if nature == "positive" else "red"
        nature_text = "Supportive" if nature == "positive" else "Challenging"
        spacer = "&nbsp;" * 15
        doc_lines.append(
            f"""<font color=\"{color}\"><b>{item.aspect} ({nature_text}) \n   Start Date: {start_date}{spacer}End Date: {end_date}{spacer}(Exact Date: {exact_date})</b></font>"""
        )
        doc_lines.append("-----"*27)
        aspect_text = item.description
        en_text = aspect_text.get(lang_code, "") if isinstance(aspect_text, dict) else ""
        # print(en_text)
        if en_text:
            doc_lines.append(en_text)
        doc_lines.append(" "*27)
        facets_text = item.facetsPoints
        if isinstance(facets_text, dict):
            for area, lang_vals in facets_text.items():
                en_vals = lang_vals.get(lang_code, []) if isinstance(lang_vals, dict) else []
                # change the case of area to Title Case and make it bold
                area_title = area.title()
                if en_vals:
                    if isinstance(en_vals, list):
                        doc_lines.append(f"<b>{area_title}:</b> {', '.join(str(val) for val in en_vals)}")
                    else:
                        doc_lines.append(f"<b>{area_title}:</b> {en_vals}")
        # doc_lines.append("====="*20)
        doc_lines.append("\n")
    document_text = "\n".join(doc_lines)
    return document_text