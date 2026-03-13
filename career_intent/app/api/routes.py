from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from career_intent.ai_agent.executioner import CareerTimingAIExecutioner
from career_intent.app.config.settings import get_settings, load_driver_catalog, load_driver_map, load_thresholds
from career_intent.app.core.compact_serializer import CompactSerializer
from career_intent.app.core.orchestrator import CareerIntentOrchestrator
from career_intent.app.schemas.input import CareerInsightRequest
from career_intent.app.schemas.output import CareerInsightOut
from career_intent.utils.file_naming import build_report_file_paths
from career_intent.utils.html_pdf_renderer import HtmlToPdfRenderer

router = APIRouter()
settings = get_settings()
orchestrator = CareerIntentOrchestrator()
compact_serializer = CompactSerializer(
    thresholds=load_thresholds(),
    driver_map=load_driver_map(),
    driver_catalog=load_driver_catalog(),
)
ai_executioner = CareerTimingAIExecutioner()
report_pdf_renderer = HtmlToPdfRenderer(enable_fallback=False)


@router.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version}


@router.get("/v1/career/startup_check")
def startup_check():
    readiness = report_pdf_renderer.readiness()
    return {
        "playwright_ok": readiness.get("playwright_ok", False),
        "weasyprint_ok": readiness.get("weasyprint_ok", False),
    }


@router.post("/v1/career/insight", response_model=CareerInsightOut)
def generate_insight(
    req: CareerInsightRequest,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    request_id = x_request_id or str(uuid.uuid4())
    return orchestrator.generate(req, request_id=request_id)


@router.post("/v1/career/insight_ai", response_model=CareerInsightOut)
def generate_insight_ai(
    req: CareerInsightRequest,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    request_id = x_request_id or str(uuid.uuid4())
    return ai_executioner.execute(req, request_id=request_id)


@router.post("/v1/career/insight_compact")
def generate_insight_compact(
    req: CareerInsightRequest,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    request_id = x_request_id or str(uuid.uuid4())
    insight = orchestrator.generate(req, request_id=request_id)
    return compact_serializer.serialize(insight, config_version=settings.app_version)


@router.get("/v1/career/driver_catalog")
def get_driver_catalog():
    return {
        "v": settings.app_version,
        "catalog": compact_serializer.get_driver_catalog(),
    }


@router.get("/v1/career/compact_schema")
def get_compact_schema():
    payload = {
        "v": settings.app_version,
        "legend": {
            "v": "version",
            "tf": "timeframe",
            "tf.s": "timeframe_start",
            "tf.e": "timeframe_end",
            "cms": "career_momentum_score",
            "sd.t": "timing_strength",
            "sd.st": "execution_stability",
            "sd.r": "risk_pressure",
            "sd.g": "growth_leverage",
            "ow": "opportunity_window",
            "cw": "caution_window",
            "ow.sc": "opportunity_score",
            "cw.sc": "caution_score",
            "ow.d": "driver_ids",
            "ti": "top_intents",
            "ti.n": "intent_name",
            "ti.sc": "intent_score",
            "ti.w": "recommended_window (o|c|n)",
            "ti.ns": "next_step",
            "ap.pre": "actions_before_opportunity",
            "ap.opp": "actions_during_opportunity",
            "ap.cau": "actions_during_caution",
            "ax": "top_aspects",
            "ax.n": "aspect_name",
            "ax.s": "start_date",
            "ax.e": "end_date",
            "ax.x": "exact_date",
            "ax.sc": "impact_score",
            "ax.c": "category_code",
            "ax.ds": "1-line summary",
            "md.id": "request_id",
            "md.h": "deterministic_hash",
            "md.ff": "fallback_flags",
        },
        "driver_catalog": compact_serializer.get_driver_catalog(),
        "category_catalog": compact_serializer.get_category_catalog(),
    }
    return JSONResponse(content=payload, headers={"Cache-Control": "public, max-age=86400"})


@router.post("/v1/career/report")
def generate_report(
    req: CareerInsightRequest,
    format: str = Query(default="html", pattern="^(html|pdf)$"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    request_id = x_request_id or str(uuid.uuid4())
    if req.user_profile is not None:
        insight = ai_executioner.execute(req, request_id=request_id)
    else:
        insight = orchestrator.generate(req, request_id=request_id)
    if not str(insight.get("name", "")).strip():
        insight["name"] = req.birth_payload.name
    html = orchestrator.render_html(insight)
    html_path, pdf_path = build_report_file_paths(req.birth_payload.name)
    try:
        result = report_pdf_renderer.html_to_pdf(html_content=html, output_pdf_path=pdf_path, output_html_path=html_path)
        pdf_bytes = Path(result.pdf_path).read_bytes()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/v1/career/report_ai")
def generate_report_ai(
    req: CareerInsightRequest,
    format: str = Query(default="html", pattern="^(html|pdf)$"),
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
):
    request_id = x_request_id or str(uuid.uuid4())
    payload = ai_executioner.execute(req, request_id=request_id)
    if not str(payload.get("name", "")).strip():
        payload["name"] = req.birth_payload.name
    html = orchestrator.render_html(payload)
    html_path, pdf_path = build_report_file_paths(req.birth_payload.name)
    try:
        result = report_pdf_renderer.html_to_pdf(html_content=html, output_pdf_path=pdf_path, output_html_path=html_path)
        pdf_bytes = Path(result.pdf_path).read_bytes()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc
    return Response(content=pdf_bytes, media_type="application/pdf")
