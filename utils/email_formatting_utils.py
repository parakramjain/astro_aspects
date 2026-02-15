from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from typing import Any, Dict, List, Optional


ALLOWED_CATEGORIES: List[str] = [
    "business_career",
    "health",
    "relationships",
    "finance",
    "family_home",
    "travel",
    "education_learning",
    "spiritual_inner_growth",
    "other",
]

CATEGORY_LABELS: Dict[str, str] = {
    "business_career": "Business / Career",
    "health": "Health",
    "relationships": "Relationships",
    "finance": "Finance",
    "family_home": "Family / Home",
    "travel": "Travel",
    "education_learning": "Education / Learning",
    "spiritual_inner_growth": "Spiritual / Inner Growth",
    "other": "Other",
}


@dataclass(frozen=True)
class RenderOptions:
    title: str = "YOUR ASTRO SNAPSHOT"
    max_bullets_per_section: int = 3


def _as_list_str(x: Any) -> List[str]:
    if isinstance(x, list):
        return [str(i) for i in x if str(i).strip()]
    if isinstance(x, str) and x.strip():
        return [x.strip()]
    return []


def _render_bullets(items: List[str], max_items: int) -> str:
    items = [i.strip() for i in items if i and i.strip()][:max_items]
    if not items:
        return ""
    lis = "".join(
        f"<li style='margin:0;line-height:1.2;color:#444;'>{escape(i)}</li>"
        for i in items
    )
    return f"<ul style='margin:2px 0 0 14px;padding:0;font-size:12px;line-height:1.2;'>{lis}</ul>"


def safe_extract_forecast_dict(raw: Any) -> Dict[str, Any]:
    """
    Input:
      - raw: either dict (already parsed) or JSON string
    Output:
      - best-effort dict
    Assumption:
      - If JSON is malformed, we hard-fail with ValueError (recommended).
    """
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from LLM: {e}") from e
    raise TypeError("raw must be dict or JSON string")


def render_basic_forecast_html_daily(raw_json: Any, opts: Optional[RenderOptions] = None) -> str:
    """
    Inputs:
      - raw_json: dict OR JSON string (must be valid JSON)
      - opts: render options
    Output:
      - Basic, deterministic HTML string suitable for email
    Reliability/Security:
      - Escapes all text.
      - Renders only allowed categories.
      - Omits empty sections automatically.
    """
    opts = opts or RenderOptions()
    data = safe_extract_forecast_dict(raw_json)

    name = escape(str(data.get("name", "")).strip() or "there")
    summary = escape(str(data.get("summary", "")).strip())
    forecast_type = escape(str(data.get("forecast_type", "")).strip())

    best_use = _as_list_str(data.get("best_use_of_day", []))
    watch_out = _as_list_str(data.get("watch_out", []))

    energy = data.get("daily_energy_score", None)
    try:
      energy_int = int(energy) if energy is not None else 0
    except (TypeError, ValueError):
        energy_int = 0
    if energy_int < 1 or energy_int > 10:
        energy_int = 0  # keep safe; optionally hard-fail

    categories_in = data.get("categories", {}) or {}
    if not isinstance(categories_in, dict):
        categories_in = {}

    # CTA
    cta = data.get("cta", {}) or {}
    site_label = escape(str(cta.get("site_label", "View full chart & guidance")).strip())
    site_url = str(cta.get("site_url", "https://www.yourastroconsultant.com")).strip() or "https://www.yourastroconsultant.com"
    footer_note = escape(str(cta.get("footer_note", "To Unsubscribe email support@yourastroconsultant.com | Preferences")).strip())

    # Render allowed categories only, omit empties
    cat_blocks: List[str] = []
    for key in ALLOWED_CATEGORIES:
        bullets = _as_list_str(categories_in.get(key, []))
        bullets_html = _render_bullets(bullets, opts.max_bullets_per_section)
        if not bullets_html:
            continue
        cat_blocks.append(
            f"""
            <div style="margin-top:14px;">
              <div style="font-size:12px;font-weight:700;color:#111;text-transform:uppercase;letter-spacing:0.4px;">
                {escape(CATEGORY_LABELS[key])}
              </div>
              {bullets_html}
            </div>
            """.strip()
        )

    best_use_html = _render_bullets(best_use, opts.max_bullets_per_section)
    watch_out_html = _render_bullets(watch_out, opts.max_bullets_per_section)

    subtitle = (
        f"<div style='margin:2px 0 0 0;font-size:11px;line-height:1.2;color:#e9ecef;text-transform:uppercase;letter-spacing:0.3px;'>{forecast_type}</div>"
        if forecast_type
        else ""
    )

    summary_block = (
        "<div style='margin:0 0 12px 0;'>"
        "<div style='margin:0 0 4px 0;font-size:14px;line-height:1.1;color:#6c757d;text-transform:uppercase;letter-spacing:0.3px;'><strong>Summary</strong></div>"
        f"<div style='margin:0;font-size:12px;line-height:1.2;color:#495057;'>{summary}</div>"
        "</div>"
        if summary
        else ""
    )

    best_use_block = (
        "<div style='margin:0 0 12px 0;'>"
        "<div style='margin:0 0 4px 0;font-size:11px;line-height:1.1;color:#28a745;text-transform:uppercase;letter-spacing:0.3px;'><strong>✓ Best use of the day</strong></div>"
        f"{best_use_html}"
        "</div>"
        if best_use_html
        else ""
    )

    watch_out_block = (
        "<div style='margin:0 0 12px 0;'>"
        "<div style='margin:0 0 4px 0;font-size:11px;line-height:1.1;color:#dc3545;text-transform:uppercase;letter-spacing:0.3px;'><strong>⚠ Watch out</strong></div>"
        f"{watch_out_html}"
        "</div>"
        if watch_out_html
        else ""
    )

    energy_block = (
        (
            "<div style='margin:0 0 16px 0;padding:8px 8px;background-color:#f8f9fa;border-left:4px solid #667eea;border-radius:4px;'>"
            "<div style='margin:0 0 6px 0;font-size:11px;line-height:1.1;font-weight:700;color:#6c757d;text-transform:uppercase;letter-spacing:0.3px;'>Daily energy score</div>"
            f"<div style='margin:0;font-size:18px;line-height:1.1;font-weight:800;color:#667eea;'>{energy_int}<span style='font-size:12px;font-weight:700;color:#adb5bd;'>/10</span></div>"
            "</div>"
        )
        if energy_int
        else ""
    )

    cats_block = (
        ("<div style='border-top:1px solid #eee;margin:6px 0 0 0;padding-top:6px;'></div>" + "".join(cat_blocks))
        if cat_blocks
        else ""
    )

    html = f"""
    <!doctype html>
    <html>
      <body style="margin:0;padding:0;background-color:#f8f9fa;font-family:Arial,Helvetica,sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
          <tr>
            <td align="center" style="padding:14px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background-color:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);border-collapse:collapse;">
                <tr>
                  <td style="padding:8px 10px 6px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:8px 8px 0 0;">
                    <div style="margin:0;font-size:18px;line-height:1.15;font-weight:325;color:#ffffff;"><strong>{escape(opts.title)}</strong></div>
                    <div style="margin:4px 0 0 0;font-size:16px;line-height:1.25;color:#e9ecef;">Hello <strong>{name}</strong>,</div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 20px 6px;">
                    {summary_block}
                    {energy_block}
                    {best_use_block}
                    {watch_out_block}
                    {cats_block}

                    <div style="border-top:1px solid #eee;margin-top:12px;padding-top:12px;font-size:11px;line-height:1.2;color:#6c757d;">
                      {site_label}: <a href="{escape(site_url)}" style="color:#667eea;text-decoration:none;font-weight:700;">{escape(site_url.replace("https://",""))}</a><br>
                      {footer_note}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """.strip()

    return html

def render_basic_forecast_html_weekly(raw_json: Any, opts: Optional[RenderOptions] = None) -> str:
    """
    Inputs:
      - raw_json: dict OR JSON string (must be valid JSON)
      - opts: render options
    Output:
      - Basic, deterministic HTML string suitable for email
    Reliability/Security:
      - Escapes all text.
      - Renders only allowed categories.
      - Omits empty sections automatically.
    """
    opts = opts or RenderOptions()
    data = safe_extract_forecast_dict(raw_json)

    name = escape(str(data.get("name", "")).strip() or "there")
    forecast_type = escape(str(data.get("forecast_type", "")).strip())

    weekly_overview = escape(str(data.get("weekly_overview", "")).strip())
    key_opportunities = _as_list_str(data.get("key_opportunities", []))
    areas_to_handle_carefully = _as_list_str(data.get("areas_to_handle_carefully", []))
    energy_trend = escape(str(data.get("energy_trend", "")).strip())
    practical_weekly_advice = _as_list_str(data.get("practical_weekly_advice", []))

    categories_in = data.get("categories", {}) or {}
    if not isinstance(categories_in, dict):
        categories_in = {}

    # CTA
    cta = data.get("cta", {}) or {}
    site_label = escape(str(cta.get("site_label", "View full chart & guidance")).strip())
    site_url = str(cta.get("site_url", "https://www.yourastroconsultant.com")).strip() or "https://www.yourastroconsultant.com"
    footer_note = escape(str(cta.get("footer_note", "To Unsubscribe email support@yourastroconsultant.com | Preferences")).strip())

    # Render allowed categories only, omit empties
    cat_blocks: List[str] = []
    for key in ALLOWED_CATEGORIES:
        bullets = _as_list_str(categories_in.get(key, []))
        bullets_html = _render_bullets(bullets, opts.max_bullets_per_section)
        if not bullets_html:
            continue
        cat_blocks.append(
            f"""
            <div style="margin-top:14px;">
              <div style="font-size:12px;font-weight:700;color:#111;text-transform:uppercase;letter-spacing:0.4px;">
                {escape(CATEGORY_LABELS[key])}
              </div>
              {bullets_html}
            </div>
            """.strip()
        )

    opportunities_html = _render_bullets(key_opportunities, opts.max_bullets_per_section)
    careful_html = _render_bullets(areas_to_handle_carefully, opts.max_bullets_per_section)
    advice_html = _render_bullets(practical_weekly_advice, opts.max_bullets_per_section)

    subtitle = (
        f"<div style='margin:2px 0 0 0;font-size:11px;line-height:1.2;color:#e9ecef;text-transform:uppercase;letter-spacing:0.3px;'>{forecast_type}</div>"
        if forecast_type
        else ""
    )

    overview_block = (
      "<div style='margin:0 0 12px 0;'>"
      "<div style='margin:0 0 4px 0;font-size:14px;line-height:1.1;color:#6c757d;text-transform:uppercase;letter-spacing:0.3px;'><strong>Weekly overview</strong></div>"
      f"<div style='margin:0;font-size:12px;line-height:1.2;color:#495057;'>{weekly_overview}</div>"
      "</div>"
      if weekly_overview
      else ""
    )

    energy_trend_block = (
      "<div style='margin:0 0 12px 0;padding:8px 8px;background-color:#f8f9fa;border-left:4px solid #667eea;border-radius:4px;'>"
      "<div style='margin:0 0 4px 0;font-size:11px;line-height:1.1;font-weight:700;color:#6c757d;text-transform:uppercase;letter-spacing:0.3px;'>Energy trend</div>"
      f"<div style='margin:0;font-size:12px;line-height:1.2;color:#495057;'>{energy_trend}</div>"
      "</div>"
      if energy_trend
      else ""
    )

    opportunities_block = (
      "<div style='margin:0 0 12px 0;'>"
      "<div style='margin:0 0 4px 0;font-size:11px;line-height:1.1;color:#28a745;text-transform:uppercase;letter-spacing:0.3px;'><strong>Key opportunities</strong></div>"
      f"{opportunities_html}"
      "</div>"
      if opportunities_html
      else ""
    )

    careful_block = (
      "<div style='margin:0 0 12px 0;'>"
      "<div style='margin:0 0 4px 0;font-size:11px;line-height:1.1;color:#dc3545;text-transform:uppercase;letter-spacing:0.3px;'><strong>Handle carefully</strong></div>"
      f"{careful_html}"
      "</div>"
      if careful_html
      else ""
    )

    advice_block = (
      "<div style='margin:0 0 12px 0;'>"
      "<div style='margin:0 0 4px 0;font-size:11px;line-height:1.1;color:#667eea;text-transform:uppercase;letter-spacing:0.3px;'><strong>Practical weekly advice</strong></div>"
      f"{advice_html}"
      "</div>"
      if advice_html
      else ""
    )

    cats_block = (
        ("<div style='border-top:1px solid #eee;margin:6px 0 0 0;padding-top:6px;'></div>" + "".join(cat_blocks))
        if cat_blocks
        else ""
    )

    html = f"""
    <!doctype html>
    <html>
      <body style="margin:0;padding:0;background-color:#f8f9fa;font-family:Arial,Helvetica,sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">
          <tr>
            <td align="center" style="padding:14px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background-color:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);border-collapse:collapse;">
                <tr>
                  <td style="padding:8px 10px 6px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:8px 8px 0 0;">
                    <div style="margin:0;font-size:18px;line-height:1.15;font-weight:325;color:#ffffff;"><strong>{escape(opts.title)}</strong></div>
                    <div style="margin:4px 0 0 0;font-size:16px;line-height:1.25;color:#e9ecef;">Hello <strong>{name}</strong>,</div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 20px 6px;">
                    {overview_block}
                    {energy_trend_block}
                    {opportunities_block}
                    {careful_block}
                    {advice_block}
                    {cats_block}

                    <div style="border-top:1px solid #eee;margin-top:12px;padding-top:12px;font-size:11px;line-height:1.2;color:#6c757d;">
                      {site_label}: <a href="{escape(site_url)}" style="color:#667eea;text-decoration:none;font-weight:700;">{escape(site_url.replace("https://",""))}</a><br>
                      {footer_note}
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """.strip()

    return html