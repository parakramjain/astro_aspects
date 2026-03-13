from __future__ import annotations

import datetime as dt
import time
from typing import Any, Dict, List

from career_intent.app.adapters.natal_adapter import NatalServiceAdapter
from career_intent.app.adapters.registry_adapter import FunctionRegistryAdapter
from career_intent.app.adapters.report_adapter import ReportServiceAdapter
from career_intent.app.config.settings import get_settings, load_driver_map, load_driver_taxonomy, load_thresholds
from career_intent.app.engines.intent_scoring import CareerIntentScoringEngine
from career_intent.app.engines.momentum import CareerMomentumEngine
from career_intent.app.engines.opportunity import OpportunityWindowEngine
from career_intent.app.engines.recommendations import ActionRecommendationGenerator
from career_intent.app.engines.risk import RiskInstabilityEngine
from career_intent.app.engines.types import WindowResult
from career_intent.app.features.feature_builder import FeatureBuilder
from career_intent.app.features.report_parser import DeterministicReportParser
from career_intent.app.reporting.html_renderer import HtmlReportRenderer
from career_intent.app.reporting.pdf_renderer import PdfReportRenderer
from career_intent.app.schemas.input import CareerInsightRequest
from career_intent.app.schemas.output import (
    ActionPlanOut,
    AstroAspectOut,
    CareerInsightOut,
    ConfidenceOut,
    IntentScoreOut,
    MetadataOut,
    ScoreBreakdownOut,
    WindowGuidanceOut,
    WindowOut,
    WindowQualityOut,
)
from career_intent.app.utils.dates import resolve_timeframe
from career_intent.app.utils.hashing import deterministic_hash
from career_intent.app.utils.logging import get_logger, log_event


class CareerIntentOrchestrator:
    def __init__(self):
        self.settings = get_settings()
        self.thresholds = load_thresholds()
        self.driver_map = load_driver_map()
        self.driver_taxonomy = load_driver_taxonomy()
        self.logger = get_logger("career_intent")
        self.registry = FunctionRegistryAdapter(self.settings.registry_path)
        self.natal_adapter = NatalServiceAdapter()
        self.report_adapter = ReportServiceAdapter()
        self.feature_builder = FeatureBuilder(DeterministicReportParser(self.driver_map, self.driver_taxonomy))
        self.opportunity_engine = OpportunityWindowEngine(self.thresholds)
        self.risk_engine = RiskInstabilityEngine(self.thresholds)
        self.momentum_engine = CareerMomentumEngine(self.thresholds)
        self.intent_engine = CareerIntentScoringEngine(self.thresholds)
        self.reco_engine = ActionRecommendationGenerator(self.thresholds)
        self.html_renderer = HtmlReportRenderer()
        self.pdf_renderer = PdfReportRenderer()

    def _clean_iso_date(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        return text[:10]

    def _pretty_aspect_name(self, raw_aspect: str) -> str:
        if not raw_aspect:
            return "Transit Influence"
        planet_map = {
            "Sun": "Sun",
            "Moo": "Moon",
            "Mer": "Mercury",
            "Ven": "Venus",
            "Mar": "Mars",
            "Jup": "Jupiter",
            "Sat": "Saturn",
            "Ura": "Uranus",
            "Nep": "Neptune",
            "Plu": "Pluto",
        }
        aspect_map = {
            "Con": "Conjunction",
            "Opp": "Opposition",
            "Sqr": "Square",
            "Tri": "Trine",
            "Sxt": "Sextile",
        }
        parts = [p for p in str(raw_aspect).split() if p]
        if len(parts) >= 3:
            transit = planet_map.get(parts[0], parts[0])
            relation = aspect_map.get(parts[1], parts[1])
            natal = planet_map.get(parts[2], parts[2])
            return f"Transit {transit} {relation} Natal {natal}"
        return str(raw_aspect)

    def _aspect_impact_score(self, item: Dict[str, Any], opp_window: WindowResult, caution_window: WindowResult) -> int:
        exact_iso = self._clean_iso_date(item.get("exactDate"))
        base = 55
        nature = str(item.get("aspectNature", "")).strip().lower()
        if nature == "positive":
            base = 65
        elif nature == "negative":
            base = 45

        exact_date = None
        if exact_iso:
            try:
                exact_date = dt.date.fromisoformat(exact_iso)
            except ValueError:
                exact_date = None

        opp_bonus = 0
        caut_penalty = 0
        if exact_date and opp_window.start_date and opp_window.end_date:
            try:
                o_start = dt.date.fromisoformat(opp_window.start_date)
                o_end = dt.date.fromisoformat(opp_window.end_date)
                if o_start <= exact_date <= o_end:
                    opp_bonus = int(round(opp_window.score * 0.20))
            except ValueError:
                opp_bonus = 0

        if exact_date and caution_window.start_date and caution_window.end_date:
            try:
                c_start = dt.date.fromisoformat(caution_window.start_date)
                c_end = dt.date.fromisoformat(caution_window.end_date)
                if c_start <= exact_date <= c_end:
                    caut_penalty = int(round(caution_window.score * 0.20))
            except ValueError:
                caut_penalty = 0

        score = base + opp_bonus - caut_penalty
        return int(max(0, min(100, score)))

    def _fallback_aspect_name(self, description: str, start_date: str, end_date: str) -> str:
        tokens = [tok.strip(" ,.;:-") for tok in description.split() if tok.strip(" ,.;:-")]
        head = " ".join(tokens[:4]).strip()
        if head:
            return f"Timeline Signal: {head.title()}"
        if start_date and end_date:
            return f"Timeline Signal: {start_date} to {end_date}"
        return "Timeline Signal"

    def _extract_astro_aspects(self, report_items: List[Dict[str, Any]], opp_window: WindowResult, caution_window: WindowResult) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        for item in report_items:
            raw_aspect = str(item.get("aspect", "")).strip()
            start_date = self._clean_iso_date(item.get("startDate"))
            end_date = self._clean_iso_date(item.get("endDate"))
            exact_date = self._clean_iso_date(item.get("exactDate")) or start_date
            description = str(item.get("description", "")).strip()
            if not start_date or not end_date:
                continue
            if not description:
                description = "Active influence period with measurable effects on execution conditions."

            aspect_name = self._pretty_aspect_name(raw_aspect) if raw_aspect else self._fallback_aspect_name(description, start_date, end_date)
            dedupe_key = (aspect_name, start_date, end_date)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            rows.append(
                {
                    "aspect_name": aspect_name,
                    "description": description,
                    "start_date": start_date,
                    "end_date": end_date,
                    "exact_date": exact_date,
                    "impact_score": self._aspect_impact_score(item, opp_window, caution_window),
                }
            )

        rows.sort(key=lambda row: (row["start_date"], row["end_date"], row["aspect_name"], row["description"]))
        return rows

    def _window_overlap_days(self, a: WindowResult, b: WindowResult) -> int:
        if not a.start_date or not b.start_date:
            return 0
        a_start = dt.date.fromisoformat(a.start_date)
        a_end = dt.date.fromisoformat(a.end_date)
        b_start = dt.date.fromisoformat(b.start_date)
        b_end = dt.date.fromisoformat(b.end_date)
        start = max(a_start, b_start)
        end = min(a_end, b_end)
        if end < start:
            return 0
        return (end - start).days + 1

    def _select_non_overlapping_windows(self, opp_candidates: list[WindowResult], risk_candidates: list[WindowResult]) -> tuple[WindowResult, WindowResult]:
        default_opp = WindowResult(start_date="", end_date="", score=0, top_drivers=[], quality=0, is_neutral=True)
        default_risk = WindowResult(start_date="", end_date="", score=0, top_drivers=[], quality=0, is_neutral=True)
        if not opp_candidates and not risk_candidates:
            return default_opp, default_risk
        if not opp_candidates:
            return default_opp, risk_candidates[0]
        if not risk_candidates:
            return opp_candidates[0], default_risk

        max_overlap_days = int(self.thresholds.get("window", {}).get("max_overlap_days", 5))
        for opp in opp_candidates:
            for risk in risk_candidates:
                overlap = self._window_overlap_days(opp, risk)
                shared_drivers = set(opp.top_drivers).intersection(set(risk.top_drivers))
                if overlap <= max_overlap_days and len(shared_drivers) <= 1:
                    return opp, risk
        return opp_candidates[0], risk_candidates[0]

    def generate(self, req: CareerInsightRequest, request_id: str) -> Dict:
        started = time.perf_counter()
        default_months = int(self.thresholds.get("default_months", 6))
        timeframe = resolve_timeframe(
            months=req.timeframe.months if req.timeframe else None,
            start_date=req.timeframe.start_date if req.timeframe else None,
            end_date=req.timeframe.end_date if req.timeframe else None,
            default_months=default_months,
        )

        payload = req.birth_payload.model_dump()
        months = req.timeframe.months if req.timeframe and req.timeframe.months else default_months

        fallback_flags = []
        feature_flags = ["quality_v2", "non_overlapping_windows", "explainability"]
        missing_payload = [
            key
            for key in ["name", "dateOfBirth", "timeOfBirth", "placeOfBirth", "timeZone"]
            if not str(payload.get(key, "")).strip()
        ]
        if missing_payload:
            fallback_flags.append("missing_payload_fields")
        natal = self.natal_adapter.compute(payload)
        fallback_flags.extend(natal.fallback_flags)

        report = self.report_adapter.fetch(payload, timeframe.start, timeframe.end, months)
        fallback_flags.extend(report.fallback_flags)

        built = self.feature_builder.build(items=report.items, start_date=timeframe.start, end_date=timeframe.end)
        fallback_flags.extend(built.summary.data_quality_flags)

        opp_series = self.opportunity_engine.compute_time_series(built.features_by_day)
        risk_series = self.risk_engine.compute_time_series(built.features_by_day)

        opp_candidates = self.opportunity_engine.rank_candidates(opp_series)
        risk_candidates = self.risk_engine.rank_candidates(risk_series)
        opp_window, caution_window = self._select_non_overlapping_windows(opp_candidates, risk_candidates)

        if not opp_window.start_date:
            opp_window = self.opportunity_engine.detect(opp_series)
        if not caution_window.start_date:
            caution_window = self.risk_engine.detect_caution_window(risk_series)

        min_opp = int(self.thresholds.get("window", {}).get("min_opportunity_score", 45))
        min_caution = int(self.thresholds.get("window", {}).get("min_caution_score", 35))
        if opp_window.score < min_opp:
            opp_window = WindowResult(
                start_date=opp_window.start_date,
                end_date=opp_window.end_date,
                score=opp_window.score,
                top_drivers=opp_window.top_drivers,
                quality=opp_window.quality,
                drivers_detail=opp_window.drivers_detail,
                is_neutral=True,
            )
        if caution_window.score < min_caution:
            caution_window = WindowResult(
                start_date=caution_window.start_date,
                end_date=caution_window.end_date,
                score=caution_window.score,
                top_drivers=caution_window.top_drivers,
                quality=caution_window.quality,
                drivers_detail=caution_window.drivers_detail,
                is_neutral=True,
            )

        opp_mean = 0.0 if not opp_series else sum(x.opportunity_score for x in opp_series) / len(opp_series)
        risk_mean = 0.0 if not risk_series else sum(x.risk_score for x in risk_series) / len(risk_series)

        score_breakdown = {
            "timing_strength": int(round(max(0.0, min(100.0, (opp_mean * 0.6) + (opp_window.score * 0.4))))),
            "execution_stability": int(round(max(0.0, min(100.0, built.summary.dimension_signals.get("execution_stability", 60.0) - (risk_mean * 0.1))))),
            "risk_pressure": int(round(max(0.0, min(100.0, (risk_mean * 0.6) + (caution_window.score * 0.4))))),
            "growth_leverage": int(round(max(0.0, min(100.0, built.summary.dimension_signals.get("growth_leverage", 50.0) + (opp_window.score * 0.1))))),
        }

        momentum = self.momentum_engine.compute(
            timing_strength=score_breakdown["timing_strength"],
            execution_stability=score_breakdown["execution_stability"],
            risk_pressure=score_breakdown["risk_pressure"],
            growth_leverage=score_breakdown["growth_leverage"],
        )

        intent_scores = self.intent_engine.compute(
            score_breakdown=score_breakdown,
            opportunity_window=opp_window,
            risk_window=caution_window,
        )
        recommendations_payload = self.reco_engine.generate(
            score_breakdown=score_breakdown,
            top_intents=intent_scores,
            opportunity_window=opp_window,
            caution_window=caution_window,
        )
        recommendations = recommendations_payload.get("summary", [])
        astro_aspects = self._extract_astro_aspects(report.items, opp_window, caution_window)

        opportunity_actions = []
        for row in opp_window.drivers_detail[:5]:
            label = str(row.get("driver_label", "priority areas")).lower()
            opportunity_actions.append(f"During {opp_window.start_date} to {opp_window.end_date}, apply focused effort to strengthen {label}.")
        if not opportunity_actions:
            opportunity_actions.append(f"Prepare execution assets before {opp_window.start_date} and activate during the opportunity window.")

        caution_actions = []
        for row in caution_window.drivers_detail[:5]:
            label = str(row.get("driver_label", "risk areas")).lower()
            caution_actions.append(f"During {caution_window.start_date} to {caution_window.end_date}, pause non-essential commitments affected by {label}.")
        if not caution_actions:
            caution_actions.append(f"Review risk controls and keep decisions reversible during {caution_window.start_date} to {caution_window.end_date}.")

        insight_highlights = [
            f"Timing strength is {score_breakdown['timing_strength']}/100 with opportunity concentrated in {opp_window.start_date} to {opp_window.end_date}.",
            f"Execution stability is {score_breakdown['execution_stability']}/100, indicating operational consistency level.",
            f"Risk pressure is {score_breakdown['risk_pressure']}/100 with caution concentrated in {caution_window.start_date} to {caution_window.end_date}.",
            f"Top near-term focus areas are {', '.join(opp_window.top_drivers[:2] or ['Baseline progress'])}.",
        ]
        if len(insight_highlights) > 5:
            insight_highlights = insight_highlights[:5]

        hash_payload = {
            "birth_payload": payload,
            "career_intent": req.career_intent,
            "timeframe": {
                "start": timeframe.start.isoformat(),
                "end": timeframe.end.isoformat(),
                "months": months,
            },
            "score_breakdown": score_breakdown,
            "opportunity_window": {
                "start_date": opp_window.start_date,
                "end_date": opp_window.end_date,
                "score": opp_window.score,
                "top_drivers": sorted(opp_window.top_drivers),
            },
            "caution_window": {
                "start_date": caution_window.start_date,
                "end_date": caution_window.end_date,
                "score": caution_window.score,
                "top_drivers": sorted(caution_window.top_drivers),
            },
            "astro_aspects": astro_aspects,
        }

        generation_ms = int((time.perf_counter() - started) * 1000)

        confidence_overall = int(
            round(
                max(
                    0.0,
                    min(
                        100.0,
                        (built.summary.confidence * 50.0)
                        + (built.summary.drivers_coverage * 35.0)
                        + ((100.0 - score_breakdown["risk_pressure"]) * 0.15),
                    ),
                )
            )
        )

        output = CareerInsightOut(
            career_momentum_score=momentum,
            opportunity_window=WindowOut(
                start_date=opp_window.start_date,
                end_date=opp_window.end_date,
                score=opp_window.score,
                top_drivers=opp_window.top_drivers[:5],
                drivers_detail=opp_window.drivers_detail[:5],
            ),
            caution_window=WindowOut(
                start_date=caution_window.start_date,
                end_date=caution_window.end_date,
                score=caution_window.score,
                top_drivers=caution_window.top_drivers[:5],
                drivers_detail=caution_window.drivers_detail[:5],
            ),
            career_intent_scores=[IntentScoreOut(**row) for row in intent_scores],
            recommendation_summary=recommendations,
            metadata=MetadataOut(
                timeframe_start=timeframe.start.isoformat(),
                timeframe_end=timeframe.end.isoformat(),
                generated_at=dt.datetime.now(dt.UTC).isoformat(),
                version=self.settings.app_version,
                deterministic_hash=deterministic_hash(hash_payload, self.settings.config_version),
                request_id=request_id,
                fallback_flags=sorted(set(fallback_flags)),
                config_version=self.settings.config_version,
                model_version="career_intent_v2",
                feature_flags=feature_flags,
                generation_ms=generation_ms,
            ),
            score_breakdown=ScoreBreakdownOut(
                timing_strength=score_breakdown["timing_strength"],
                execution_stability=score_breakdown["execution_stability"],
                risk_pressure=score_breakdown["risk_pressure"],
                growth_leverage=score_breakdown["growth_leverage"],
                labels=["timing_strength", "execution_stability", "risk_pressure", "growth_leverage"],
            ),
            insight_highlights=insight_highlights[:5],
            window_guidance=WindowGuidanceOut(
                opportunity_actions=opportunity_actions[:5],
                caution_actions=caution_actions[:5],
            ),
            confidence=ConfidenceOut(
                overall=confidence_overall,
                drivers_coverage=int(round(built.summary.drivers_coverage * 100.0)),
                data_quality_flags=sorted(set(built.summary.data_quality_flags)),
            ),
            window_quality=WindowQualityOut(
                opportunity_window_quality=opp_window.quality,
                caution_window_quality=caution_window.quality,
            ),
            action_plan=ActionPlanOut(**recommendations_payload.get("action_plan", {})),
            astro_aspects=[AstroAspectOut(**row) for row in astro_aspects],
        )
        payload_out = output.model_dump()
        log_event(
            self.logger,
            "career_intent_generated",
            request_id=request_id,
            timeframe_start=payload_out["metadata"]["timeframe_start"],
            timeframe_end=payload_out["metadata"]["timeframe_end"],
            fallback_flags=payload_out["metadata"].get("fallback_flags", []),
        )
        return payload_out

    def render_html(self, insight: Dict) -> str:
        return self.html_renderer.render(insight)

    def render_pdf(self, insight: Dict):
        return self.pdf_renderer.render(insight)
