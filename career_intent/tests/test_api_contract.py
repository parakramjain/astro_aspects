from fastapi.testclient import TestClient
import datetime as dt
from pypdf import PdfWriter

from career_intent.app.adapters.natal_adapter import NatalAdapterResult
from career_intent.app.adapters.report_adapter import ReportAdapterResult
from career_intent.app.main import app


client = TestClient(app)


def _write_dummy_pdf(path: str) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with open(path, "wb") as handle:
        writer.write(handle)


def _overlap_days(a_start: str, a_end: str, b_start: str, b_end: str) -> int:
    a_s = dt.date.fromisoformat(a_start)
    a_e = dt.date.fromisoformat(a_end)
    b_s = dt.date.fromisoformat(b_start)
    b_e = dt.date.fromisoformat(b_end)
    start = max(a_s, b_s)
    end = min(a_e, b_e)
    if end < start:
        return 0
    return (end - start).days + 1


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_startup_check_renderer_readiness(monkeypatch):
    from career_intent.app.api import routes

    monkeypatch.setattr(
        routes.report_pdf_renderer,
        "readiness",
        lambda: {"playwright_ok": True, "weasyprint_ok": False},
    )

    resp = client.get("/v1/career/startup_check")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"playwright_ok": True, "weasyprint_ok": False}


def test_insight_contract_and_deterministic_hash(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={"ok": True}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        items = []
        for day in range(1, 91):
            stamp = f"2026-01-{min(day, 28):02d}T00:00:00" if day <= 28 else (
                f"2026-02-{min(day - 28, 28):02d}T00:00:00" if day <= 56 else f"2026-03-{min(day - 56, 31):02d}T00:00:00"
            )
            items.append(
                {
                    "startDate": stamp,
                    "endDate": stamp,
                    "aspectNature": "Positive" if day <= 35 else ("Negative" if day >= 60 else "Neutral"),
                    "description": (
                        "Strong growth with visibility and networking momentum"
                        if day <= 35
                        else (
                            "Execution pressure with delays and instability"
                            if day >= 60
                            else "Steady progress with mixed signals"
                        )
                    ),
                }
            )
        return ReportAdapterResult(
            items=items
        )

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6, "start_date": "2026-01-01", "end_date": "2026-06-30"},
    }

    headers = {"X-Request-ID": "req-123"}
    r1 = client.post("/v1/career/insight", json=body, headers=headers)
    r2 = client.post("/v1/career/insight", json=body, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200

    p1 = r1.json()
    p2 = r2.json()

    assert p1["career_momentum_score"] >= 0
    assert isinstance(p1["recommendation_summary"], list)
    assert "astro_aspects" in p1
    assert isinstance(p1["astro_aspects"], list)
    assert p1["astro_aspects"]
    first_aspect = p1["astro_aspects"][0]
    assert set(first_aspect.keys()) == {
        "aspect_name",
        "description",
        "start_date",
        "end_date",
        "exact_date",
        "impact_score",
    }
    assert first_aspect["aspect_name"].startswith("Transit ") or first_aspect["aspect_name"].startswith("Timeline Signal:")
    assert 0 <= first_aspect["impact_score"] <= 100
    assert len(p1["recommendation_summary"]) == len(set(p1["recommendation_summary"]))
    assert len(p1["opportunity_window"]["top_drivers"]) == len(set(p1["opportunity_window"]["top_drivers"]))
    assert len(p1["caution_window"]["top_drivers"]) == len(set(p1["caution_window"]["top_drivers"]))
    assert p1["metadata"]["deterministic_hash"] == p2["metadata"]["deterministic_hash"]
    assert p1["metadata"]["request_id"] == "req-123"

    overlap = _overlap_days(
        p1["opportunity_window"]["start_date"],
        p1["opportunity_window"]["end_date"],
        p1["caution_window"]["start_date"],
        p1["caution_window"]["end_date"],
    )
    assert overlap <= 5

    reasons = [row["short_reason"] for row in p1["career_intent_scores"][:3]]
    assert len(reasons) == len(set(reasons))

    stable_1 = {k: v for k, v in p1.items() if k != "metadata"}
    stable_2 = {k: v for k, v in p2.items() if k != "metadata"}
    assert stable_1 == stable_2


def test_report_html(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        return ReportAdapterResult(items=[])

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)

    def fake_render_to_pdf(html_content: str, output_pdf_path: str, output_html_path: str | None = None, options=None):
        if output_html_path:
            from pathlib import Path

            Path(output_html_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_html_path).write_text(html_content, encoding="utf-8")
        _write_dummy_pdf(output_pdf_path)
        return type(
            "R",
            (),
            {
                "pdf_path": output_pdf_path,
                "html_path": output_html_path or output_pdf_path.replace(".pdf", ".html"),
                "success": True,
                "file_size_bytes": 1,
                "page_count": 1,
                "render_engine": "playwright",
                "generation_ms": 1,
            },
        )()

    monkeypatch.setattr(routes.report_pdf_renderer, "html_to_pdf", fake_render_to_pdf)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Skill Building",
        "timeframe": {"months": 6},
    }

    resp = client.post("/v1/career/report?format=html", json=body)
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers.get("content-type", "")
    assert resp.content[:4] == b"%PDF"


def test_insight_distinct_window_drivers_when_data_supports(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={"ok": True}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        items = []
        for day in range(1, 75):
            month = "01" if day <= 25 else ("02" if day <= 50 else "03")
            day_in_month = day if day <= 25 else (day - 25 if day <= 50 else day - 50)
            stamp = f"2026-{month}-{day_in_month:02d}T00:00:00"
            if day <= 25:
                desc = "Growth, visibility, leadership, and networking momentum"
                nature = "Positive"
            elif day <= 50:
                desc = "Execution pressure, delay risk, and instability"
                nature = "Negative"
            else:
                desc = "Mixed period with moderate progress"
                nature = "Neutral"
            items.append({"startDate": stamp, "endDate": stamp, "aspectNature": nature, "description": desc})
        return ReportAdapterResult(items=items)

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6, "start_date": "2026-01-01", "end_date": "2026-03-31"},
    }

    resp = client.post("/v1/career/insight", json=body)
    assert resp.status_code == 200
    payload = resp.json()

    opp = set(payload["opportunity_window"]["top_drivers"])
    caution = set(payload["caution_window"]["top_drivers"])
    assert opp
    assert caution
    assert opp != caution


def test_astro_aspects_from_timeline_items(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={"ok": True}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        return ReportAdapterResult(
            items=[
                {
                    "aspect": "Jup Tri Sun",
                    "startDate": "2026-07-10T00:00:00",
                    "exactDate": "2026-07-20T00:00:00",
                    "endDate": "2026-08-12T00:00:00",
                    "aspectNature": "Positive",
                    "description": "A period supportive of expansion, confidence, and visible progress through constructive efforts.",
                },
                {
                    "aspect": "Sat Sqr Mer",
                    "startDate": "2026-08-15T00:00:00",
                    "exactDate": "2026-08-20T00:00:00",
                    "endDate": "2026-09-05T00:00:00",
                    "aspectNature": "Negative",
                    "description": "A period requiring tighter structure, clearer communication, and controlled workload pacing.",
                },
            ]
        )

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6, "start_date": "2026-07-01", "end_date": "2026-12-31"},
    }

    r1 = client.post("/v1/career/insight", json=body)
    r2 = client.post("/v1/career/insight", json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200

    p1 = r1.json()
    p2 = r2.json()
    assert p1["astro_aspects"] == p2["astro_aspects"]
    assert len(p1["astro_aspects"]) == 2
    assert p1["astro_aspects"][0]["aspect_name"] == "Transit Jupiter Trine Natal Sun"
    assert p1["astro_aspects"][0]["exact_date"] == "2026-07-20"


def test_compact_endpoint_and_driver_catalog(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={"ok": True}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        return ReportAdapterResult(
            items=[
                {
                    "aspect": "Jup Tri Sun",
                    "startDate": "2026-07-10T00:00:00",
                    "exactDate": "2026-07-20T00:00:00",
                    "endDate": "2026-08-12T00:00:00",
                    "aspectNature": "Positive",
                    "description": "Supports expansion and visible progress.",
                }
            ]
        )

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6, "start_date": "2026-07-01", "end_date": "2026-12-31"},
    }

    resp = client.post("/v1/career/insight_compact", json=body, headers={"X-Request-ID": "req-compact"})
    assert resp.status_code == 200
    payload = resp.json()
    assert set(payload.keys()) == {"v", "tf", "cms", "sd", "ow", "cw", "ti", "ap", "ax", "md"}
    assert payload["md"]["id"] == "req-compact"
    assert isinstance(payload["ow"]["d"], list)

    cat_resp = client.get("/v1/career/driver_catalog")
    assert cat_resp.status_code == 200
    cat = cat_resp.json()
    assert "catalog" in cat
    assert isinstance(cat["catalog"], dict)


def test_compact_schema_contract_and_cache_headers(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={"ok": True}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        return ReportAdapterResult(
            items=[
                {
                    "aspect": "Jup Tri Sun",
                    "startDate": "2026-07-10T00:00:00",
                    "exactDate": "2026-07-20T00:00:00",
                    "endDate": "2026-08-12T00:00:00",
                    "aspectNature": "Positive",
                    "description": "Supports expansion and visible progress.",
                }
            ]
        )

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6, "start_date": "2026-07-01", "end_date": "2026-12-31"},
    }

    compact_resp = client.post("/v1/career/insight_compact", json=body)
    assert compact_resp.status_code == 200
    compact = compact_resp.json()

    schema_resp = client.get("/v1/career/compact_schema")
    assert schema_resp.status_code == 200
    assert schema_resp.headers.get("cache-control") == "public, max-age=86400"
    schema = schema_resp.json()

    assert set(schema.keys()) == {"v", "legend", "driver_catalog", "category_catalog"}
    assert "tf.s" in schema["legend"]
    assert "ax.ds" in schema["legend"]
    assert set(schema["category_catalog"].keys()) == {"g", "e", "s", "p", "l", "o"}

    compact_driver_ids = set(compact["ow"]["d"] + compact["cw"]["d"])
    assert compact_driver_ids.issubset(set(schema["driver_catalog"].keys()))

    assert all(row["c"] in schema["category_catalog"] for row in compact["ax"])
    assert all(len(row["ds"]) <= 90 for row in compact["ax"])


def test_insight_ai_endpoint_returns_full_schema(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={"ok": True}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        return ReportAdapterResult(
            items=[
                {
                    "aspect": "Jup Tri Sun",
                    "startDate": "2026-07-10T00:00:00",
                    "exactDate": "2026-07-20T00:00:00",
                    "endDate": "2026-08-12T00:00:00",
                    "aspectNature": "Positive",
                    "description": "Supports expansion and visible progress.",
                }
            ]
        )

    def fake_execute(req, request_id: str):
        return routes.orchestrator.generate(req, request_id=request_id)

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)
    monkeypatch.setattr(routes.ai_executioner, "execute", fake_execute)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6, "start_date": "2026-07-01", "end_date": "2026-12-31"},
    }

    resp = client.post("/v1/career/insight_ai", json=body, headers={"X-Request-ID": "req-ai"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["metadata"]["request_id"] == "req-ai"
    assert "opportunity_window" in payload
    assert "caution_window" in payload
    assert "career_intent_scores" in payload
    assert "astro_aspects" in payload


def test_report_ai_renders_html_from_insight_payload(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={"ok": True}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        return ReportAdapterResult(
            items=[
                {
                    "aspect": "Jup Tri Sun",
                    "startDate": "2026-07-10T00:00:00",
                    "exactDate": "2026-07-20T00:00:00",
                    "endDate": "2026-08-12T00:00:00",
                    "aspectNature": "Positive",
                    "description": "Supports expansion and visible progress.",
                }
            ]
        )

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)

    def fake_render_to_pdf(html_content: str, output_pdf_path: str, output_html_path: str | None = None, options=None):
        if output_html_path:
            from pathlib import Path

            Path(output_html_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_html_path).write_text(html_content, encoding="utf-8")
        _write_dummy_pdf(output_pdf_path)
        return type(
            "R",
            (),
            {
                "pdf_path": output_pdf_path,
                "html_path": output_html_path or output_pdf_path.replace(".pdf", ".html"),
                "success": True,
                "file_size_bytes": 1,
                "page_count": 1,
                "render_engine": "playwright",
                "generation_ms": 1,
            },
        )()

    monkeypatch.setattr(routes.report_pdf_renderer, "html_to_pdf", fake_render_to_pdf)

    def fake_execute(req, request_id: str):
        return routes.orchestrator.generate(req, request_id=request_id)

    monkeypatch.setattr(routes.ai_executioner, "execute", fake_execute)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6, "start_date": "2026-07-01", "end_date": "2026-12-31"},
    }

    report_resp = client.post("/v1/career/report_ai?format=html", json=body, headers={"X-Request-ID": "req-report-ai"})
    assert report_resp.status_code == 200
    assert "application/pdf" in report_resp.headers.get("content-type", "")
    assert report_resp.content[:4] == b"%PDF"


def test_report_and_report_ai_accept_user_profile(monkeypatch):
    from career_intent.app.api import routes

    def fake_natal(_payload):
        return NatalAdapterResult(chart={"ok": True}, aspects=[])

    def fake_report(_payload, _start, _end, _months):
        return ReportAdapterResult(items=[])

    def fake_execute(req, request_id: str):
        return routes.orchestrator.generate(req, request_id=request_id)

    monkeypatch.setattr(routes.orchestrator.natal_adapter, "compute", fake_natal)
    monkeypatch.setattr(routes.orchestrator.report_adapter, "fetch", fake_report)
    monkeypatch.setattr(routes.ai_executioner, "execute", fake_execute)

    def fake_render_to_pdf(html_content: str, output_pdf_path: str, output_html_path: str | None = None, options=None):
        if output_html_path:
            from pathlib import Path

            Path(output_html_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_html_path).write_text(html_content, encoding="utf-8")
        _write_dummy_pdf(output_pdf_path)
        return type(
            "R",
            (),
            {
                "pdf_path": output_pdf_path,
                "html_path": output_html_path or output_pdf_path.replace(".pdf", ".html"),
                "success": True,
                "file_size_bytes": 1,
                "page_count": 1,
                "render_engine": "playwright",
                "generation_ms": 1,
            },
        )()

    monkeypatch.setattr(routes.report_pdf_renderer, "html_to_pdf", fake_render_to_pdf)

    body = {
        "birth_payload": {
            "name": "Amit",
            "dateOfBirth": "1991-07-14",
            "timeOfBirth": "22:35:00",
            "placeOfBirth": "Mumbai, IN",
            "timeZone": "Asia/Kolkata",
            "latitude": 19.076,
            "longitude": 72.8777,
            "lang_code": "en",
        },
        "career_intent": "Promotion",
        "timeframe": {"months": 6},
        "user_profile": {
            "current_role_title": "Senior Data Scientist",
            "target_roles": ["GenAI Architect"],
            "constraints": ["No relocation"],
            "time_available_hours_per_week": 6,
            "tone_preference": "practical",
        },
    }

    r1 = client.post("/v1/career/report?format=html", json=body)
    r2 = client.post("/v1/career/report_ai?format=html", json=body)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert "application/pdf" in r1.headers.get("content-type", "")
    assert "application/pdf" in r2.headers.get("content-type", "")
