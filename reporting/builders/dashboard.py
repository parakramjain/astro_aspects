from __future__ import annotations

from typing import Any, Dict, List, Tuple

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from ..config import ReportConfig
from ..components import section_header
from ..i18n import lang_for_text, section_title, t
from ..normalize import get_lang_text, smart_no_orphan_last_word
from ..schema import ReportJson
from ..styles import PALETTE


AREA_MAP: List[Tuple[str, str, str, str]] = [
    ("career", "करियर", "Career", "★"),
    ("relationships", "रिश्ते", "Relationships", "❤"),
    ("money", "धन", "Money", "₹"),
    ("health_adj", "स्वास्थ्य", "Health", "✚"),
]


def _area_bullets(area_value: Any, config: ReportConfig) -> Tuple[List[str], List[str]]:
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"

    if isinstance(area_value, dict):
        hi_list = area_value.get("hi") or area_value.get("HI")
        en_list = area_value.get("en") or area_value.get("EN")

        def _coerce(v: Any, pref: str) -> List[str]:
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
            if isinstance(v, str) and v.strip():
                return [s.strip() for s in v.split("\n") if s.strip()]
            return []

        return _coerce(hi_list, "hi"), _coerce(en_list, "en")

    if isinstance(area_value, list):
        return ([str(x).strip() for x in area_value if str(x).strip()], [])

    if isinstance(area_value, str) and area_value.strip():
        return ([area_value.strip()], [])

    return ([], [])


def _truncate(text: str, max_chars: int) -> str:
    s = (text or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _has_text(value: Any, config: ReportConfig) -> bool:
    preferred = "hi" if config.language_mode in {"HI", "BILINGUAL"} else "en"
    fallback = "en" if preferred == "hi" else "hi"
    txt = get_lang_text(value, preferred=preferred, fallback=fallback)
    return bool(txt and txt.strip() and txt.strip() != "—")


def _score_by_area(items: List[Any], config: ReportConfig) -> Dict[str, Tuple[int, int]]:
    out = {key: (0, 0) for key, _, _, _ in AREA_MAP}
    for it in items:
        nature = str(getattr(it, "aspectNature", "")).strip().lower()
        is_pos = nature == "positive"
        is_neg = nature in {"negative", "challenging"}
        facets = getattr(it, "facetsPoints", None)
        if not isinstance(facets, dict):
            continue
        for key, _, _, _ in AREA_MAP:
            if _has_text(facets.get(key), config):
                pos, neg = out[key]
                if is_pos:
                    pos += 1
                elif is_neg:
                    neg += 1
                out[key] = (pos, neg)
    return out


def build_dashboard_story(data: ReportJson, config: ReportConfig, styles: Dict[str, any]) -> List:
    story: List = []
    story.append(section_header(section_title("life_areas", config), styles))
    story.append(Spacer(1, 6))

    areas = data.dailyWeekly.areas or {}

    score_map = _score_by_area(data.timeline.items or [], config)

    cards: List = []
    for key, title_hi, title_en, symbol in AREA_MAP:
        raw = areas.get(key)
        bullets_hi, bullets_en = _area_bullets(raw, config)
        preferred_bullets = bullets_hi if config.language_mode in {"HI", "BILINGUAL"} else bullets_en
        if config.language_mode == "EN":
            preferred_bullets = bullets_en or bullets_hi
        if config.language_mode == "HI":
            preferred_bullets = bullets_hi or bullets_en
        preferred_bullets = [
            _truncate(str(b), config.max_bullet_chars) for b in (preferred_bullets or []) if str(b).strip()
        ]
        preferred_bullets = preferred_bullets[: config.max_card_bullets]

        title = title_en if lang_for_text(config.language_mode) == "EN" else title_hi
        pos, neg = score_map.get(key, (0, 0))
        score_line = Paragraph(f"{symbol} {title}  <font color='{PALETTE.muted}'>+{pos}  -{neg}</font>", styles["subheader"])

        card_lines: List = [score_line]
        for b in preferred_bullets:
            card_lines.append(Paragraph(f"• {smart_no_orphan_last_word(b)}", styles["body"]))

        if len(card_lines) == 1:
            lang = lang_for_text(config.language_mode)
            card_lines.append(Paragraph(f"• {t('no_major_signals', lang)}", styles["body"]))

        card = Table([[card_lines]], colWidths=[None])
        card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALETTE.card_bg),
                    ("BOX", (0, 0), (-1, -1), 0.5, PALETTE.divider),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        cards.append(card)

    # 2x2 dashboard grid. Keep it as a simple nested-table layout to ensure it can be wrapped
    # and measured correctly by ReportLab.
    grid = Table(
        [
            [cards[0], cards[1]],
            [cards[2], cards[3]],
        ],
        colWidths=[None, None],
    )
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                # Base paddings
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # Visual spacing between the 2 columns and 2 rows (approx 10pt)
                ("RIGHTPADDING", (0, 0), (0, -1), 10),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 1), (-1, 1), 10),
            ]
        )
    )

    story.append(grid)
    return story
