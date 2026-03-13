from __future__ import annotations

import re
from html.parser import HTMLParser

from career_intent.app.reporting.html_renderer import HtmlReportRenderer


class _TagTracker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)


def _sample_insight() -> dict:
    return {
        "career_momentum_score": 74,
        "opportunity_window": {
            "start_date": "2026-07-20",
            "end_date": "2026-08-17",
            "score": 66,
            "top_drivers": ["Stakeholder alignment", "Execution velocity"],
            "drivers_detail": [
                {
                    "driver_label": "Stakeholder alignment",
                    "category": "Opportunity",
                    "polarity": "positive",
                    "impact_score": 66,
                    "evidence_snippet": "Collaboration support is elevated.",
                }
            ],
        },
        "caution_window": {
            "start_date": "2026-08-10",
            "end_date": "2026-08-25",
            "score": 58,
            "top_drivers": ["Workload pressure", "Decision latency"],
            "drivers_detail": [
                {
                    "driver_label": "Workload pressure",
                    "category": "Stability",
                    "polarity": "negative",
                    "impact_score": 58,
                    "evidence_snippet": "Parallel commitments may reduce focus.",
                }
            ],
        },
        "career_intent_scores": [
            {
                "intent_name": "Promotion",
                "score": 68,
                "short_reason": "Advancement potential improves with strong execution discipline.",
                "recommended_window": "opportunity",
                "next_step": "Negotiate measurable impact targets with leadership.",
            },
            {
                "intent_name": "Skill Building",
                "score": 63,
                "short_reason": "Capability compounding benefits from focused execution.",
                "recommended_window": "neutral",
                "next_step": "Build one portfolio-grade proof of work.",
            },
        ],
        "recommendation_summary": [
            "Apply focused effort during priority windows.",
            "Prepare key outcomes before execution period.",
            "Track weekly progress against milestones.",
        ],
        "score_breakdown": {
            "timing_strength": 72,
            "execution_stability": 74,
            "risk_pressure": 35,
            "growth_leverage": 67,
            "labels": ["timing_strength", "execution_stability", "risk_pressure", "growth_leverage"],
        },
        "insight_highlights": [
            "Timing peak occurs between Jul 20 and Aug 17.",
            "Execution stability is strong (74/100).",
            "Risk pressure is currently controlled.",
        ],
        "window_guidance": {
            "opportunity_actions": [
                "Apply for high-impact opportunities.",
                "Negotiate scope with leadership.",
                "Focus on stakeholder alignment.",
            ],
            "caution_actions": [
                "Avoid expanding commitments outside priority outcomes.",
                "Shorten decision cycles and validate assumptions.",
            ],
        },
        "action_plan": {
            "now_to_opportunity_start": [
                "Prepare decision brief.",
                "Build measurable portfolio proof.",
            ],
            "during_opportunity": [
                "Execute highest-impact work.",
                "Confirm ownership and timeline.",
            ],
            "during_caution": [
                "Pause non-critical commitments.",
                "Review workload and remove low-value tasks.",
            ],
        },
        "confidence": {"overall": 76, "drivers_coverage": 68, "data_quality_flags": []},
        "window_quality": {"opportunity_window_quality": 71, "caution_window_quality": 64},
        "metadata": {
            "timeframe_start": "2026-03-01",
            "timeframe_end": "2026-08-31",
            "generated_at": "2026-03-04T10:15:00+00:00",
            "version": "1.0.0",
            "deterministic_hash": "abc123",
            "request_id": "req-1",
        },
    }


def test_renders_six_month_cards_for_six_month_timeframe():
    html = HtmlReportRenderer().render(_sample_insight())
    assert html.count('class="timeline-card"') == 6
    assert "Mar 2026" in html
    assert "Aug 2026" in html


def test_clips_cross_month_windows_in_timeline():
    html = HtmlReportRenderer().render(_sample_insight())
    assert "Jul 20 – Jul 31" in html
    assert "Aug 01 – Aug 17" in html


def test_each_month_contains_actions_list():
    html = HtmlReportRenderer().render(_sample_insight())
    assert html.count('class="timeline-card"') == 6
    assert html.count('month-actions-title">Actions') == 6


def test_timeline_uses_action_plan_and_shows_generated_timestamp():
    html = HtmlReportRenderer().render(_sample_insight())
    assert "Prepare decision brief." in html
    assert "Execute highest-impact work." in html
    assert "Pause non-critical commitments." in html
    assert "10:15" in html


def test_opportunity_and_caution_windows_appear_in_timeline():
    html = HtmlReportRenderer().render(_sample_insight())
    assert "Opportunity Window" in html
    assert "Caution Window" in html


def test_renders_valid_html_shell():
    html = HtmlReportRenderer().render(_sample_insight())
    parser = _TagTracker()
    parser.feed(html)
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "html" in parser.tags
    assert "head" in parser.tags
    assert "body" in parser.tags


def test_css_media_query_is_weasyprint_compatible():
    html = HtmlReportRenderer().render(_sample_insight())
    assert "@media screen and (max-width: 980px)" in html


def test_renders_hero_narrative_version_and_top_priority_card():
    html = HtmlReportRenderer().render(_sample_insight())
    assert 'data-report-version="v2.0.0"' in html
    assert "hero-narrative" in html
    assert "Your #1 Career Move Right Now" in html


def test_kpi_cards_include_explanations_and_drivers():
    html = HtmlReportRenderer().render(_sample_insight())
    assert "kpi-explainer" in html
    assert "kpi-drivers" in html
    assert "Career Momentum" in html


def test_driver_impact_scores_are_ranked_and_differentiated():
    html = HtmlReportRenderer().render(_sample_insight())
    impacts = [int(score) for score in re.findall(r"<tr><td>[^<]+</td><td>[^<]+</td><td>(\d+)</td><td>", html)]
    assert impacts
    assert impacts == sorted(impacts, reverse=True)
    assert len(set(impacts)) == len(impacts)


def test_timeline_strip_share_card_and_countdown_hooks_render():
    html = HtmlReportRenderer().render(_sample_insight())
    assert "timeline-strip" in html
    assert "Download as Image" in html
    assert "data-phase=\"prepare\"" in html
    assert "summaryExportStatus" in html
