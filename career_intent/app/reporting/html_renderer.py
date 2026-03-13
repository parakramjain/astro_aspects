from __future__ import annotations

import datetime as dt
import logging
from html import escape
from typing import Dict, List

from .date_utils import (
    build_day_strip,
    clip_window,
    fmt_date,
    fmt_datetime,
    fmt_short_date,
    iter_months,
    month_start,
    next_month,
    normalize_windows,
    phase_countdown,
    resolve_reference_date,
    to_date,
)
from .narrative_utils import (
    build_closed_window_takeaway,
    build_driver_practical_meaning,
    build_hero_narrative,
    build_kpi_explanation,
    dedupe_lines,
    html_list,
    period_signal_label,
)
from .scoring_utils import direction_of_change, pick_top_priority_intent, rank_and_spread_driver_scores


REPORT_VERSION = "v2.0.0"


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(float(value))
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return default


def _slugify(raw: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in raw.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "career-window"


def _render_table_scroll(table_html: str) -> str:
    return f'<div class="table-scroll">{table_html}</div>'


class HtmlReportRenderer:
    def __init__(self) -> None:
        self.logger = logging.getLogger("career_intent_html_renderer")

    def render(self, insight: Dict) -> str:
        try:
            return self._render(insight)
        except Exception:
            self.logger.exception("Failed to render career timing HTML report")
            raise

    def _render(self, insight: Dict) -> str:
        opp = insight.get("opportunity_window", {})
        caution = insight.get("caution_window", {})
        meta = insight.get("metadata", {})
        confidence = insight.get("confidence", {})
        window_quality = insight.get("window_quality", {})
        score_breakdown = insight.get("score_breakdown", {})
        window_guidance = insight.get("window_guidance", {})
        action_plan = insight.get("action_plan", {})
        user_profile = insight.get("user_profile", {}) if isinstance(insight.get("user_profile"), dict) else {}

        timeframe_start = to_date(str(meta.get("timeframe_start") or ""))
        timeframe_end = to_date(str(meta.get("timeframe_end") or ""))
        report_date = resolve_reference_date(meta, timeframe_start)

        if not timeframe_start:
            timeframe_start = month_start(report_date)
        if not timeframe_end or timeframe_end < timeframe_start:
            timeframe_end = timeframe_start + dt.timedelta(days=89)

        months = iter_months(timeframe_start, timeframe_end)
        timeframe_days = (timeframe_end - timeframe_start).days + 1
        timeframe_label = f"{timeframe_days}-day period"

        user_name = (
            str((insight.get("user") or {}).get("name") or "").strip()
            if isinstance(insight.get("user"), dict)
            else ""
        ) or str(meta.get("name") or insight.get("name") or "").strip() or "You"

        opp_score = _safe_int(opp.get("score", 0))
        caution_score = _safe_int(caution.get("score", 0))
        momentum = _safe_int(insight.get("career_momentum_score", 0))
        confidence_score = _safe_int(confidence.get("overall", 0))
        opp_quality = _safe_int(window_quality.get("opportunity_window_quality", 0))
        caution_quality = _safe_int(window_quality.get("caution_window_quality", 0))
        quality_indicator = _safe_int(round((opp_quality + caution_quality) / 2.0))

        opp_windows = list(normalize_windows(insight.get("opportunity_windows") or opp))
        caution_windows = list(normalize_windows(insight.get("caution_windows") or caution))

        if not opp_windows:
          opp_start = to_date(str(opp.get("start_date") or ""))
          opp_end = to_date(str(opp.get("end_date") or ""))
          if opp_start and opp_end:
            opp_windows = [(opp_start, opp_end)]
        if not caution_windows:
          caution_start_window = to_date(str(caution.get("start_date") or ""))
          caution_end_window = to_date(str(caution.get("end_date") or ""))
          if caution_start_window and caution_end_window:
            caution_windows = [(caution_start_window, caution_end_window)]

        intent_rows_raw = [row for row in (insight.get("career_intent_scores") or []) if isinstance(row, dict)]
        top_intent = pick_top_priority_intent(
            intent_rows_raw,
            opportunity_window=opp,
            caution_window=caution,
            report_date=report_date,
        )

        primary_intent = str((top_intent or {}).get("intent_name") or "").strip()
        if not primary_intent and intent_rows_raw:
            primary_intent = str(intent_rows_raw[0].get("intent_name") or "").strip()

        hero_period_signal = period_signal_label(opp_score, caution_score)
        hero_narrative = build_hero_narrative(
            user_name=user_name,
            primary_intent=primary_intent,
            timeframe_label=timeframe_label,
            period_signal=hero_period_signal,
        )

        highlights = [str(item).strip() for item in (insight.get("insight_highlights") or []) if str(item).strip()]
        highlights = highlights[:5] if highlights else [
            f"Your best execution window in this report runs {fmt_date(opp.get('start_date'))} to {fmt_date(opp.get('end_date'))}.",
            "Weekly consistency will matter more than one-time bursts of effort.",
            "Use caution periods to tighten scope and protect decision quality.",
        ]

        strengths = [str(item).strip() for item in (user_profile.get("strengths") or []) if str(item).strip()]
        gaps = [str(item).strip() for item in (user_profile.get("gaps") or user_profile.get("skill_gaps") or []) if str(item).strip()]

        opp_actions = dedupe_lines(
            [str(x) for x in (window_guidance.get("opportunity_actions") or [])],
            [
                "Push one visible, high-leverage move while the opportunity window is open.",
                "Secure stakeholder alignment before expanding execution scope.",
            ],
        )
        caution_actions = dedupe_lines(
            [str(x) for x in (window_guidance.get("caution_actions") or [])],
            [
                "Delay irreversible decisions unless there is a hard business need.",
                "Pressure-test assumptions in short review cycles.",
            ],
        )
        plan_prepare = dedupe_lines(
            [str(x) for x in (action_plan.get("now_to_opportunity_start") or [])],
            [
                "Define one measurable outcome for your top career move.",
                "Prepare proof of impact before outreach or negotiation.",
            ],
        )
        plan_execute = dedupe_lines(
            [str(x) for x in (action_plan.get("during_opportunity") or [])],
            ["Execute your top-priority move while timing support is strongest."],
        )
        plan_caution = dedupe_lines(
            [str(x) for x in (action_plan.get("during_caution") or [])],
            ["Narrow commitments and protect focus during caution periods."],
        )

        opportunity_start = to_date(str(opp.get("start_date") or ""))
        opportunity_end = to_date(str(opp.get("end_date") or ""))
        caution_start = to_date(str(caution.get("start_date") or ""))
        caution_end = to_date(str(caution.get("end_date") or ""))

        timing_strength = _safe_int(score_breakdown.get("timing_strength", 0))
        execution_stability = _safe_int(score_breakdown.get("execution_stability", 0))
        risk_pressure = _safe_int(score_breakdown.get("risk_pressure", 0))
        growth_leverage = _safe_int(score_breakdown.get("growth_leverage", 0))

        top_positive = str((opp.get("top_drivers") or ["timing alignment"])[0])
        top_negative = str((caution.get("top_drivers") or ["execution drag"])[0])
        trend_text = direction_of_change(
            report_date=report_date,
            opportunity_start=opportunity_start,
            caution_start=caution_start,
        )

        kpis = [
            {
                "label": "Career Momentum",
                "score": momentum,
                "positive_driver": top_positive,
                "negative_driver": top_negative,
                "direction_of_change": trend_text,
            },
            {
                "label": "Confidence",
                "score": confidence_score,
                "positive_driver": f"drivers coverage at {_safe_int(confidence.get('drivers_coverage', 0))}/100",
                "negative_driver": ", ".join((confidence.get("data_quality_flags") or [])[:1]),
                "direction_of_change": "Confidence improves as evidence quality improves across weekly checkpoints.",
            },
            {
                "label": "Window Quality",
                "score": quality_indicator,
                "positive_driver": f"opportunity quality at {opp_quality}/100",
                "negative_driver": f"caution pressure at {caution_quality}/100",
                "direction_of_change": trend_text,
            },
            {
                "label": "Execution Stability",
                "score": execution_stability,
                "positive_driver": "consistency in execution routines",
                "negative_driver": "risk pressure" if risk_pressure > 0 else "",
                "direction_of_change": direction_of_change(
                    report_date=report_date,
                    opportunity_start=opportunity_start,
                    caution_start=caution_start,
                ),
            },
        ]

        kpi_cards = "".join(
            """
            <article class="kpi-card">
              <div class="kpi-score">{score}/100</div>
              <div class="kpi-label">{label}</div>
              <p class="kpi-explainer">{explanation}</p>
              <div class="kpi-drivers">+ {positive}<br/>− {negative}</div>
            </article>
            """.format(
                score=escape(str(kpi["score"])),
                label=escape(str(kpi["label"])),
                explanation=escape(
                    build_kpi_explanation(
                        label=str(kpi["label"]),
                        score=int(kpi["score"]),
                        positive_driver=str(kpi["positive_driver"]),
                        negative_driver=str(kpi["negative_driver"]),
                        direction_of_change=str(kpi["direction_of_change"]),
                    )
                ),
                positive=escape(str(kpi["positive_driver"] or "Notable support is developing.")),
                negative=escape(str(kpi["negative_driver"] or "No dominant drag signal.")),
            )
            for kpi in kpis
        )

        intent_rows_html: List[str] = []
        for idx, row in enumerate(intent_rows_raw):
            row_class = "top-intent" if idx < 2 else ""
            intent_rows_html.append(
                "<tr class=\"{cls}\"><td>{intent}</td><td>{score}</td><td>{window}</td><td>{reason}</td><td>{next_step}</td></tr>".format(
                    cls=row_class,
                    intent=escape(str(row.get("intent_name", ""))),
                    score=escape(str(_safe_int(row.get("score", 0)))),
                    window=escape(str(row.get("recommended_window", "neutral")).title()),
                    reason=escape(str(row.get("short_reason", "Strengthen evidence before committing."))),
                    next_step=escape(str(row.get("next_step", "Track progress weekly and adapt."))),
                )
            )

        top_window_start = to_date(str((top_intent or {}).get("window_start") or "")) or (
            opportunity_start if str((top_intent or {}).get("recommended_window") or "").strip().lower() != "caution" else caution_start
        )
        top_window_end = to_date(str((top_intent or {}).get("window_end") or "")) or (
            opportunity_end if str((top_intent or {}).get("recommended_window") or "").strip().lower() != "caution" else caution_end
        )
        top_next_action = str((top_intent or {}).get("next_step") or "Commit one concrete move this week and define a measurable success signal.")
        top_reason = str((top_intent or {}).get("short_reason") or "This move has the best balance of timing support and execution feasibility right now.")

        top_priority_card = ""
        if top_intent:
            top_priority_card = """
            <div class="priority-card">
              <div class="priority-eyebrow">Your #1 Career Move Right Now</div>
              <div class="priority-title">{intent}</div>
              <div class="priority-meta">Score: <strong>{score}/100</strong> · Window: {start} – {end}</div>
              <div class="priority-action"><strong>Next action:</strong> {action}</div>
              <p class="priority-why">{why}</p>
            </div>
            """.format(
                intent=escape(str(top_intent.get("intent_name") or "Top priority intent")),
                score=escape(str(_safe_int(top_intent.get("score", 0)))),
                start=escape(fmt_date(top_window_start.isoformat() if top_window_start else "")),
                end=escape(fmt_date(top_window_end.isoformat() if top_window_end else "")),
                action=escape(top_next_action),
                why=escape(top_reason),
            )

        raw_drivers: List[Dict] = []
        for source_name, source_window in (("Opportunity", opp), ("Caution", caution)):
            details = source_window.get("drivers_detail") or []
            if details:
                for item in details:
                    label = str(item.get("driver_label") or "").strip()
                    if not label:
                        continue
                    raw_drivers.append(
                        {
                            "driver_label": label,
                            "category": str(item.get("category") or source_name),
                            "impact_score": _safe_int(item.get("impact_score", source_window.get("score", 0))),
                            "polarity": str(item.get("polarity") or ("positive" if source_name == "Opportunity" else "negative")),
                            "evidence": str(item.get("evidence_snippet") or "").strip(),
                        }
                    )
            else:
                for idx, label in enumerate((source_window.get("top_drivers") or [])[:5]):
                    raw_drivers.append(
                        {
                            "driver_label": str(label),
                            "category": source_name,
                            "impact_score": _safe_int(source_window.get("score", 0)) - idx,
                            "polarity": "positive" if source_name == "Opportunity" else "negative",
                            "evidence": "",
                        }
                    )

        ranked_drivers = rank_and_spread_driver_scores(raw_drivers)
        driver_rows = "".join(
            "<tr><td>{label}</td><td>{category}</td><td>{impact}</td><td>{meaning}</td></tr>".format(
                label=escape(str(row.get("label") or row.get("driver_label") or "")),
                category=escape(str(row.get("category") or "General")),
                impact=escape(str(_safe_int(row.get("impact_score", 0)))),
                meaning=escape(build_driver_practical_meaning(row, insight)),
            )
            for row in ranked_drivers[:10]
        )

        timeline_cards: List[str] = []
        for current_month_start in months:
            current_month_end = next_month(current_month_start) - dt.timedelta(days=1)
            if current_month_end > timeframe_end:
                current_month_end = timeframe_end

            month_entries: List[str] = []
            opp_clip = clip_window(opp, current_month_start, current_month_end)
            caution_clip = clip_window(caution, current_month_start, current_month_end)

            if opp_clip:
                month_entries.append(
                    """
                    <div class="window-entry opportunity">
                      <div class="window-type">Opportunity Window</div>
                      <div class="window-range">{start} – {end}</div>
                      <div class="window-score">Score: {score}</div>
                    </div>
                    """.format(start=fmt_short_date(opp_clip[0]), end=fmt_short_date(opp_clip[1]), score=opp_score)
                )
            if caution_clip:
                month_entries.append(
                    """
                    <div class="window-entry caution">
                      <div class="window-type">Caution Window</div>
                      <div class="window-range">{start} – {end}</div>
                      <div class="window-score">Score: {score}</div>
                    </div>
                    """.format(start=fmt_short_date(caution_clip[0]), end=fmt_short_date(caution_clip[1]), score=caution_score)
                )
            if not month_entries:
                month_entries.append(
                    """
                    <div class="window-entry neutral">
                      <div class="window-type">Neutral Build Phase</div>
                      <div class="window-range">{start} – {end}</div>
                      <div class="window-score">Focus: Build readiness</div>
                    </div>
                    """.format(start=fmt_short_date(current_month_start), end=fmt_short_date(current_month_end))
                )

            month_actions: List[str] = []
            month_watchouts: List[str] = []
            if opportunity_start and current_month_end < opportunity_start:
                month_actions.extend(plan_prepare[:3])
            if opp_clip:
                month_actions.extend(plan_execute[:3])
                month_actions.extend(opp_actions[:2])
            if caution_clip:
                month_actions.extend(plan_caution[:2])
                month_watchouts.extend(caution_actions[:3])
            if not month_watchouts:
                month_watchouts.append("Avoid adding commitments that do not support your top intent.")
            if not month_actions:
                month_actions.extend([
                    "Advance one visible skill or portfolio proof point.",
                    "Keep outreach focused on high-relevance conversations.",
                ])

            month_actions = dedupe_lines(month_actions, ["Maintain weekly progress against a single measurable goal."])
            month_watchouts = dedupe_lines(month_watchouts, ["Avoid scattered effort."])

            timeline_cards.append(
                """
                <article class="timeline-card">
                  <h4>{month_name}</h4>
                  <div class="month-windows">{entries}</div>
                  <div class="month-actions-title">Actions</div>
                  <ul class="month-actions">{actions}</ul>
                  <div class="month-actions-title">Watch Outs</div>
                  <ul class="month-actions">{watchouts}</ul>
                </article>
                """.format(
                    month_name=escape(current_month_start.strftime("%b %Y")),
                    entries="".join(month_entries),
                    actions=html_list(month_actions[:4]),
                    watchouts=html_list(month_watchouts[:3]),
                )
            )

        day_strip = build_day_strip(timeframe_start, timeframe_end, opp_windows, caution_windows)
        month_day_counts: Dict[str, int] = {}
        for item in day_strip:
            key = item.date.strftime("%b %Y")
            month_day_counts[key] = month_day_counts.get(key, 0) + 1

        month_labels = "".join(
            '<div class="month-label" style="flex:{days};">{label}</div>'.format(
                days=days,
                label=escape(label),
            )
            for label, days in month_day_counts.items()
        )
        day_blocks = "".join(
            '<div class="timeline-day {state}" title="{title}" aria-label="{title}"></div>'.format(
                state=escape(item.state),
                title=escape(f"{item.date.isoformat()}: {item.label}"),
            )
            for item in day_strip
        )

        prepare_countdown = phase_countdown("prepare", report_date, opportunity_start, opportunity_start)
        execute_countdown = phase_countdown("execute", report_date, opportunity_start, opportunity_end)
        caution_countdown = phase_countdown("caution", report_date, caution_start, caution_end)

        past_section_html = ""
        lookback_start = report_date - dt.timedelta(days=60)
        lookback_end = report_date - dt.timedelta(days=30)
        historical_windows: List[tuple[dt.date, dt.date]] = []
        historical_windows.extend([window for window in opp_windows if window[1] >= lookback_start and window[0] <= lookback_end])
        past_window = sorted(historical_windows, key=lambda win: win[1], reverse=True)[0] if historical_windows else None

        future_opp = sorted([window for window in opp_windows if window[0] > report_date], key=lambda win: win[0])
        upcoming_window = future_opp[0] if future_opp else None
        if past_window:
            past_label = f"{fmt_short_date(past_window[0])} – {fmt_short_date(past_window[1])}"
            next_label = f"{fmt_short_date(upcoming_window[0])} – {fmt_short_date(upcoming_window[1])}" if upcoming_window else "upcoming"
            past_section_html = """
            <section class="section subtle-section">
              <h2>A Window Like This Just Closed</h2>
              <div class="past-window-dates">{dates}</div>
              <p>{meaning}</p>
              <p class="muted">{takeaway}</p>
            </section>
            """.format(
                dates=escape(past_label),
                meaning=escape(
                    build_closed_window_takeaway(
                        window_label=past_label,
                        next_window_label=next_label,
                        primary_intent=primary_intent,
                        strengths=strengths,
                        gaps=gaps,
                    )
                ),
                takeaway=escape("Windows are time-bound. Start preparing now so your next window converts into visible progress."),
            )

        recommendation_summary = dedupe_lines([str(x) for x in insight.get("recommendation_summary", [])], [])
        decision_signals = [
            f"Timing Strength: {timing_strength}/100",
            f"Execution Stability: {execution_stability}/100",
            f"Risk Pressure: {risk_pressure}/100",
            f"Growth Leverage: {growth_leverage}/100",
        ]
        if execution_stability >= 70:
            decision_signals.append("Execution conditions are supportive. Prioritize delivery over exploration.")
        if risk_pressure >= 65:
            decision_signals.append("Risk pressure is elevated. Keep commitments selective until pressure cools.")

        share_opportunity = f"{fmt_date(opp.get('start_date'))} – {fmt_date(opp.get('end_date'))}"
        share_caution = f"{fmt_date(caution.get('start_date'))} – {fmt_date(caution.get('end_date'))}"
        share_action = top_next_action

        cta = insight.get("upsell") or insight.get("cta") or {}
        full_report_price = str(cta.get("full_report_price") or "$49")
        alerts_price = str(cta.get("alerts_price") or "$9/month")
        full_report_url = str(cta.get("full_report_url") or "#")
        alerts_url = str(cta.get("alerts_url") or "#")

        future_windows = sorted([window for window in opp_windows if window[0] > report_date], key=lambda item: item[0])
        next_major_window = future_windows[0] if future_windows else (opp_windows[0] if opp_windows else None)
        if next_major_window:
          next_start, next_end = next_major_window
          days_to_next = max(0, (next_start - report_date).days)
          months_to_next = max(1, round(days_to_next / 30)) if days_to_next else 0
          if months_to_next > 0:
            upsell_headline = f"Your next major career window opens in about {months_to_next} month{'s' if months_to_next != 1 else ''}."
          else:
            upsell_headline = f"Your next major career window is active from {fmt_short_date(next_start)} to {fmt_short_date(next_end)}."
        else:
          upsell_headline = "Your next major career window is approaching — plan beyond the next 90 days."

        report_generated_text = fmt_datetime(str(meta.get("report_generated_at") or meta.get("generated_at") or ""))
        filename = f"career-window-{_slugify(user_name)}.png"

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>Career Timing Intelligence — Your Personalized Plan</title>
<style>
:root {{
  --bg: #f8fafc;
  --surface: #ffffff;
  --surface-soft: #f1f5f9;
  --text: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;
  --brand: #0f766e;
  --opportunity: #16a34a;
  --caution: #dc2626;
  --neutral: #94a3b8;
  --radius: 14px;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--text); font-family: Inter, Segoe UI, Arial, sans-serif; line-height: 1.45; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 20px 16px 32px; }}
h1 {{ margin: 0; font-size: 1.85rem; letter-spacing: -0.02em; }}
h2 {{ margin: 0 0 10px; font-size: 1.2rem; letter-spacing: -0.01em; }}
h3 {{ margin: 0 0 8px; font-size: 1.05rem; }}
h4 {{ margin: 0 0 8px; font-size: 0.98rem; }}
.section {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; margin-top: 14px; }}
.hero-title {{ display: grid; gap: 6px; }}
.hero-subtitle {{ color: var(--muted); font-size: 0.95rem; }}
.hero-meta {{ color: var(--muted); font-size: 0.82rem; }}
.hero-narrative {{ margin: 10px 0 0; background: linear-gradient(90deg, #ecfeff 0%, #f0fdf4 100%); border: 1px solid #ccfbf1; border-radius: 12px; padding: 12px; font-size: 0.98rem; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }}
.kpi-card {{ border: 1px solid var(--border); border-radius: 12px; padding: 12px; background: var(--surface-soft); }}
.kpi-score {{ font-size: 1.45rem; font-weight: 750; }}
.kpi-label {{ margin-top: 2px; font-weight: 620; }}
.kpi-explainer {{ margin: 8px 0 0; color: #334155; font-size: 0.86rem; }}
.kpi-drivers {{ margin-top: 8px; color: var(--muted); font-size: 0.8rem; }}
ul {{ margin: 0; padding-left: 18px; }}
li {{ margin: 5px 0; }}
.subtle-section {{ background: #fcfcfd; border-color: #e5e7eb; }}
.window-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.window-card {{ border: 1px solid var(--border); border-radius: 12px; padding: 12px; }}
.window-card.opportunity {{ background: #f0fdf4; }}
.window-card.caution {{ background: #fef2f2; }}
.timeline-month-labels {{ display: flex; gap: 1px; margin-bottom: 6px; color: var(--muted); font-size: 0.76rem; text-transform: uppercase; }}
.month-label {{ text-align: center; }}
.timeline-strip {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(8px, 1fr)); gap: 1px; background: var(--surface-soft); padding: 6px; border-radius: 10px; border: 1px solid var(--border); }}
.timeline-day {{ width: 100%; height: 10px; border-radius: 2px; background: var(--neutral); }}
.timeline-day.opportunity {{ background: var(--opportunity); }}
.timeline-day.caution {{ background: var(--caution); }}
.timeline-day.neutral {{ background: #cbd5e1; }}
.timeline-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }}
.timeline-card {{ border: 1px solid var(--border); border-radius: 12px; padding: 12px; background: #fff; }}
.window-entry {{ border-left: 4px solid #94a3b8; background: #f8fafc; padding: 7px 9px; margin-bottom: 7px; border-radius: 8px; }}
.window-entry.opportunity {{ border-left-color: var(--opportunity); }}
.window-entry.caution {{ border-left-color: var(--caution); }}
.window-entry.neutral {{ border-left-color: var(--neutral); }}
.window-type {{ font-weight: 650; }}
.window-score {{ color: #475569; font-size: 0.8rem; }}
.month-actions-title {{ margin-top: 8px; font-weight: 700; font-size: 0.88rem; }}
.month-actions {{ margin-top: 4px; }}
.priority-card {{ background: linear-gradient(130deg, #0f172a 0%, #1e293b 100%); color: #f8fafc; border-radius: 14px; padding: 14px; margin-bottom: 10px; }}
.priority-eyebrow {{ font-size: 0.75rem; letter-spacing: 0.05em; text-transform: uppercase; opacity: 0.8; }}
.priority-title {{ margin-top: 6px; font-size: 1.3rem; font-weight: 750; }}
.priority-meta {{ margin-top: 4px; color: #e2e8f0; font-size: 0.9rem; }}
.priority-action {{ margin-top: 8px; font-size: 0.9rem; }}
.priority-why {{ margin: 8px 0 0; color: #cbd5e1; font-size: 0.86rem; }}
.table-scroll {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
table {{ width: 100%; border-collapse: collapse; min-width: 700px; }}
th, td {{ border: 1px solid var(--border); padding: 8px; text-align: left; vertical-align: top; font-size: 0.84rem; }}
th {{ background: #f8fafc; font-weight: 650; }}
.top-intent td {{ background: #fff7ed; }}
.phase-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
.phase-card {{ border: 1px solid var(--border); border-radius: 12px; padding: 12px; background: var(--surface-soft); }}
.phase-countdown {{ margin: 8px 0 0; font-size: 0.83rem; color: #334155; }}
.share-card {{ border: 1px solid var(--border); border-radius: 14px; padding: 14px; background: #ffffff; max-width: 520px; margin: 0 auto; text-align: center; }}
.share-title {{ font-size: 1.05rem; font-weight: 700; margin-bottom: 6px; }}
.share-meta {{ color: #334155; font-size: 0.9rem; margin: 4px 0; }}
.share-action {{ margin-top: 8px; color: #0f172a; font-weight: 620; }}
.share-controls {{ margin-top: 10px; display: flex; justify-content: center; gap: 8px; }}
.btn {{ border: none; border-radius: 10px; padding: 10px 14px; cursor: pointer; font-weight: 640; }}
.btn-primary {{ background: #0f766e; color: #fff; }}
.btn-primary:hover, .btn-primary:focus {{ background: #0d9488; }}
.btn-outline {{ background: #fff; color: #0f172a; border: 1px solid #94a3b8; }}
.btn-outline:hover, .btn-outline:focus {{ background: #f8fafc; }}
.upsell-card {{ border: 1px solid #bae6fd; background: linear-gradient(180deg, #ecfeff 0%, #f8fafc 100%); border-radius: 16px; padding: 16px; }}
.upsell-title {{ font-size: 1.25rem; font-weight: 750; margin-bottom: 4px; }}
.upsell-copy {{ color: #334155; margin-bottom: 12px; }}
.cta-row {{ display: flex; gap: 10px; flex-wrap: wrap; }}
.qa-note {{ margin-top: 10px; color: var(--muted); font-size: 0.74rem; text-align: right; }}
.muted {{ color: var(--muted); }}
@media screen and (max-width: 980px) {{
  .kpi-grid, .window-grid, .timeline-grid, .phase-grid {{ grid-template-columns: 1fr; }}
}}
@media screen and (max-width: 640px) {{
  main {{ padding: 12px 10px 24px; }}
  .section {{ padding: 12px; margin-top: 10px; }}
  h1 {{ font-size: 1.45rem; }}
  .hero-narrative {{ font-size: 0.92rem; }}
  .timeline-strip {{ grid-template-columns: repeat(auto-fit, minmax(6px, 1fr)); gap: 1px; padding: 5px; }}
  .timeline-day {{ height: 8px; }}
  .cta-row {{ flex-direction: column; }}
  .btn {{ width: 100%; }}
  .qa-note {{ text-align: left; }}
}}
</style>
</head>
<body data-report-version=\"{escape(REPORT_VERSION)}\" data-report-date=\"{escape(report_date.isoformat())}\">
<main>
  <section class=\"section\">
    <div class=\"hero-title\">
      <h1>Career Timing Intelligence — Your Personalized Plan</h1>
      <div class=\"hero-subtitle\">Your 3-Month Career Execution Roadmap</div>
      <div class=\"hero-meta\">Name: {escape(user_name)} · Timeframe: {escape(fmt_date(meta.get('timeframe_start')))} → {escape(fmt_date(meta.get('timeframe_end')))} · Generated: {escape(report_generated_text)}</div>
    </div>
    <p class=\"hero-narrative\">{escape(hero_narrative)}</p>
    <div class=\"kpi-grid\">{kpi_cards}</div>
  </section>

  <section class=\"section\">
    <h2>Key Observations</h2>
    <ul>{html_list(highlights, prefix='✔ ')}</ul>
  </section>

  {past_section_html}

  <section class=\"section\">
    <h2>Opportunity vs Caution Windows</h2>
    <div class=\"window-grid\">
      <article class=\"window-card opportunity\">
        <h3>Opportunity Window</h3>
        <div>{escape(fmt_date(opp.get('start_date')))} – {escape(fmt_date(opp.get('end_date')))}</div>
        <div>Score: {opp_score}/100</div>
        <div>Top Drivers: {escape(', '.join((opp.get('top_drivers') or [])[:5]) or 'N/A')}</div>
        <div><strong>Recommended Moves</strong></div>
        <ul>{html_list(opp_actions[:5])}</ul>
      </article>
      <article class=\"window-card caution\">
        <h3>Caution Window</h3>
        <div>{escape(fmt_date(caution.get('start_date')))} – {escape(fmt_date(caution.get('end_date')))}</div>
        <div>Score: {caution_score}/100</div>
        <div>Top Drivers: {escape(', '.join((caution.get('top_drivers') or [])[:5]) or 'N/A')}</div>
        <div><strong>Risk Controls</strong></div>
        <ul>{html_list(caution_actions[:5])}</ul>
      </article>
    </div>
  </section>

  <section class=\"section\">
    <h2>Month-by-Month Career Timeline</h2>
    <div class=\"timeline-month-labels\">{month_labels}</div>
    <div class=\"timeline-strip\" role=\"img\" aria-label=\"Opportunity and caution day strip. Red takes precedence on overlap days.\">{day_blocks}</div>
    <div class=\"timeline-grid\">{''.join(timeline_cards)}</div>
  </section>

  <section class=\"section\">
    <h2>Career Intent Priority</h2>
    {top_priority_card}
    {_render_table_scroll(
      '<table><thead><tr><th>Intent</th><th>Score</th><th>Recommended Window</th><th>Why it matters</th><th>Next Step</th></tr></thead><tbody>' + ''.join(intent_rows_html) + '</tbody></table>'
    )}
  </section>

  <section class=\"section\">
    <h2>Action Roadmap</h2>
    <div class=\"phase-grid\">
      <article class=\"phase-card\">
        <h3>Prepare Phase</h3>
        <div class=\"muted\">now → opportunity start</div>
        <div class=\"phase-countdown\" data-phase=\"prepare\" data-start=\"{escape(opportunity_start.isoformat() if opportunity_start else '')}\" data-end=\"{escape(opportunity_start.isoformat() if opportunity_start else '')}\">{escape(prepare_countdown)}</div>
        <ul>{html_list(plan_prepare[:4], prefix='☐ ')}</ul>
      </article>
      <article class=\"phase-card\">
        <h3>Execute Phase</h3>
        <div class=\"muted\">during opportunity window</div>
        <div class=\"phase-countdown\" data-phase=\"execute\" data-start=\"{escape(opportunity_start.isoformat() if opportunity_start else '')}\" data-end=\"{escape(opportunity_end.isoformat() if opportunity_end else '')}\">{escape(execute_countdown)}</div>
        <ul>{html_list(plan_execute[:4], prefix='☐ ')}</ul>
      </article>
      <article class=\"phase-card\">
        <h3>Caution Phase</h3>
        <div class=\"muted\">during caution window</div>
        <div class=\"phase-countdown\" data-phase=\"caution\" data-start=\"{escape(caution_start.isoformat() if caution_start else '')}\" data-end=\"{escape(caution_end.isoformat() if caution_end else '')}\">{escape(caution_countdown)}</div>
        <ul>{html_list(plan_caution[:4], prefix='☐ ')}</ul>
      </article>
    </div>
  </section>

  <section class=\"section\">
    <h2>Driver Explanation</h2>
    {_render_table_scroll('<table><thead><tr><th>Driver</th><th>Category</th><th>Impact</th><th>Practical Meaning</th></tr></thead><tbody>' + driver_rows + '</tbody></table>')}
  </section>

  <section class=\"section\">
    <h2>Decision Signals</h2>
    <ul>{html_list(decision_signals)}</ul>
    <div><strong>Priority Summary</strong></div>
    <ul>{html_list(recommendation_summary)}</ul>
  </section>

  <section class=\"section\">
    <h2>Shareable Career Window Snapshot</h2>
    <div class=\"share-card\" id=\"shareSummaryCard\">
      <div class=\"share-title\">{escape(user_name)} · Career Timing Snapshot</div>
      <div class=\"share-meta\"><strong>Top Intent:</strong> {escape(primary_intent or 'Career Advancement')}</div>
      <div class=\"share-meta\"><strong>Opportunity:</strong> {escape(share_opportunity)}</div>
      <div class=\"share-meta\"><strong>Caution:</strong> {escape(share_caution)}</div>
      <div class=\"share-action\">{escape(share_action)}</div>
    </div>
    <div class=\"share-controls\">
      <button type=\"button\" class=\"btn btn-outline\" id=\"downloadSummaryBtn\" data-file-name=\"{escape(filename)}\">Download as Image</button>
    </div>
    <div class=\"muted\" id=\"summaryExportStatus\"></div>
  </section>

  <section class=\"section upsell-card\">
    <div class=\"upsell-title\">{escape(upsell_headline)}</div>
    <div class=\"upsell-copy\">This 3-month plan helps you execute the next move. A 12-month plan helps you sequence multiple moves, avoid dead zones, and compound outcomes across the full year.</div>
    <div class=\"cta-row\">
      <a class=\"btn btn-primary\" href=\"{escape(full_report_url)}\">Get My 12-Month Report — {escape(full_report_price)}</a>
      <a class=\"btn btn-outline\" href=\"{escape(alerts_url)}\">Enable Monthly Career Alerts — {escape(alerts_price)}</a>
    </div>
    <div class=\"qa-note\">Generated {escape(report_generated_text)} · Report version {escape(REPORT_VERSION)}</div>
  </section>
</main>

<script src=\"https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js\"></script>
<script>
(function () {{
  function parseDate(raw) {{
    if (!raw) return null;
    const dt = new Date(raw + 'T00:00:00');
    return isNaN(dt.getTime()) ? null : dt;
  }}

  function daysBetween(a, b) {{
    const msPerDay = 24 * 60 * 60 * 1000;
    return Math.floor((b.getTime() - a.getTime()) / msPerDay);
  }}

  function fmtDate(dateObj) {{
    return dateObj.toLocaleDateString(undefined, {{ month: 'short', day: '2-digit', year: 'numeric' }});
  }}

  function phaseMessage(phase, reportDate, startDate, endDate) {{
    if (phase === 'prepare') {{
      if (!startDate) return 'Preparation window is available now.';
      if (reportDate < startDate) return '⏳ ' + daysBetween(reportDate, startDate) + ' days left to prepare before your window opens.';
      if (!endDate || reportDate <= endDate) return 'Preparation phase is already underway.';
      return 'Preparation phase has passed.';
    }}
    if (phase === 'execute') {{
      if (!startDate || !endDate) return 'Execution timing is being refined.';
      if (reportDate < startDate) return '🚀 ' + (daysBetween(startDate, endDate) + 1) + ' days available in this execution window.';
      if (reportDate <= endDate) return '🚀 This execution phase is active now — ' + (daysBetween(reportDate, endDate) + 1) + ' days remaining.';
      return 'This execution phase has passed.';
    }}
    if (phase === 'caution') {{
      if (!startDate) return 'No caution phase is scheduled in this timeframe.';
      if (reportDate < startDate) return '⚠️ Caution begins on ' + fmtDate(startDate) + '. Plan commitments carefully before then.';
      if (!endDate || reportDate <= endDate) return '⚠️ Caution phase is active now. Keep commitments tightly scoped.';
      return 'Caution phase has passed.';
    }}
    return '';
  }}

  const reportDateRaw = document.body.getAttribute('data-report-date');
  const reportDate = parseDate(reportDateRaw) || new Date();
  document.querySelectorAll('.phase-countdown').forEach(function (node) {{
    const phase = node.getAttribute('data-phase') || '';
    const startDate = parseDate(node.getAttribute('data-start') || '');
    const endDate = parseDate(node.getAttribute('data-end') || '');
    node.textContent = phaseMessage(phase, reportDate, startDate, endDate);
  }});

  const exportButton = document.getElementById('downloadSummaryBtn');
  const summaryCard = document.getElementById('shareSummaryCard');
  const status = document.getElementById('summaryExportStatus');

  if (exportButton && summaryCard) {{
    exportButton.addEventListener('click', function () {{
      if (typeof html2canvas === 'undefined') {{
        if (status) status.textContent = 'Image export is unavailable right now. Please take a screenshot instead.';
        return;
      }}
      html2canvas(summaryCard, {{ backgroundColor: '#ffffff', scale: 2 }})
        .then(function (canvas) {{
          const link = document.createElement('a');
          const fileName = exportButton.getAttribute('data-file-name') || 'career-window-summary.png';
          link.download = fileName;
          link.href = canvas.toDataURL('image/png');
          link.click();
          if (status) status.textContent = 'Summary card downloaded.';
        }})
        .catch(function () {{
          if (status) status.textContent = 'Image export failed. Please take a screenshot as fallback.';
        }});
    }});
  }}
}})();
</script>
</body>
</html>"""
