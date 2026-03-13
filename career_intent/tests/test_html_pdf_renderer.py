from __future__ import annotations

import types
from pathlib import Path

import pytest
from pypdf import PdfWriter

from career_intent.utils.file_naming import build_report_file_paths
from career_intent.utils.html_pdf_renderer import HtmlToPdfRenderer


def _write_dummy_pdf(path: str) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with open(path, "wb") as handle:
        writer.write(handle)


def test_save_html_writes_content(tmp_path: Path):
    renderer = HtmlToPdfRenderer()
    html_path = tmp_path / "nested" / "report.html"
    out = renderer.save_html("<html><body>hello</body></html>", str(html_path))
    assert Path(out).exists()
    assert "hello" in Path(out).read_text(encoding="utf-8")


def test_html_to_pdf_creates_pdf_and_metadata(monkeypatch, tmp_path: Path):
    renderer = HtmlToPdfRenderer()

    def fake_render(input_html_path: str, output_pdf_path: str, options):
        assert Path(input_html_path).exists()
        _write_dummy_pdf(output_pdf_path)

    monkeypatch.setattr(renderer, "_render_pdf_with_playwright", fake_render)

    pdf_path = tmp_path / "out" / "report.pdf"
    result = renderer.html_to_pdf("<html><body>x</body></html>", str(pdf_path))

    assert result.success is True
    assert Path(result.html_path).exists()
    assert Path(result.pdf_path).exists()
    assert result.file_size_bytes > 0
    assert result.render_engine == "playwright"


def test_output_directories_auto_created(monkeypatch, tmp_path: Path):
    renderer = HtmlToPdfRenderer()

    def fake_render(_input_html_path: str, output_pdf_path: str, _options):
        _write_dummy_pdf(output_pdf_path)

    monkeypatch.setattr(renderer, "_render_pdf_with_playwright", fake_render)

    pdf_path = tmp_path / "a" / "b" / "c" / "report.pdf"
    renderer.html_to_pdf("<html><body>ok</body></html>", str(pdf_path))
    assert pdf_path.exists()


def test_failure_preserves_html_file(monkeypatch, tmp_path: Path):
    renderer = HtmlToPdfRenderer(enable_fallback=False)

    def fail_render(_input_html_path: str, _output_pdf_path: str, _options):
        raise RuntimeError("render failed")

    monkeypatch.setattr(renderer, "_render_pdf_with_playwright", fail_render)

    pdf_path = tmp_path / "report.pdf"
    with pytest.raises(RuntimeError):
        renderer.html_to_pdf("<html><body>debug me</body></html>", str(pdf_path))

    assert pdf_path.with_suffix(".html").exists()


def test_dual_engine_failure_has_actionable_message(monkeypatch, tmp_path: Path):
    renderer = HtmlToPdfRenderer(enable_fallback=True)
    monkeypatch.setattr(renderer, "readiness", lambda: {"playwright_ok": True, "weasyprint_ok": True})

    def fail_playwright(_input_html_path: str, _output_pdf_path: str, _options):
        raise RuntimeError("Playwright is not available")

    def fail_weasy(_input_html_path: str, _output_pdf_path: str):
        raise RuntimeError("WeasyPrint is not available")

    monkeypatch.setattr(renderer, "_render_pdf_with_playwright", fail_playwright)
    monkeypatch.setattr(renderer, "_render_pdf_with_weasyprint", fail_weasy)

    html_path = tmp_path / "in.html"
    html_path.write_text("<html><body>x</body></html>", encoding="utf-8")
    pdf_path = tmp_path / "out.pdf"

    with pytest.raises(RuntimeError) as exc:
        renderer.html_file_to_pdf(str(html_path), str(pdf_path))

    message = str(exc.value)
    assert "both playwright and fallback weasyprint" in message


def test_file_naming_helper_and_html_fallback_derivation(tmp_path: Path):
    html_path, pdf_path = build_report_file_paths("Amit Jain", output_dir=tmp_path)
    assert html_path.endswith("amit_jain_career_progression_report.html")
    assert pdf_path.endswith("amit_jain_career_progression_report.pdf")

    renderer = HtmlToPdfRenderer()
    derived_html = renderer._resolve_html_path(pdf_path, None)
    assert derived_html.endswith(".html")
    assert Path(derived_html).name == Path(pdf_path).with_suffix(".html").name


def test_normalize_html_for_weasyprint_media_query():
    renderer = HtmlToPdfRenderer()
    html = "<style>@media (max-width: 980px) {.x{display:block;}}</style>"
    out = renderer._normalize_html_for_weasyprint(html)
    assert "@media print" in out


def test_skips_playwright_when_not_ready_and_uses_weasy(monkeypatch, tmp_path: Path):
    renderer = HtmlToPdfRenderer(enable_fallback=True)

    monkeypatch.setattr(renderer, "readiness", lambda: {"playwright_ok": False, "weasyprint_ok": True})

    def fail_playwright(_input_html_path: str, _output_pdf_path: str, _options):
        raise AssertionError("playwright should be skipped when not ready")

    def ok_weasy(_input_html_path: str, output_pdf_path: str):
        _write_dummy_pdf(output_pdf_path)

    monkeypatch.setattr(renderer, "_render_pdf_with_playwright", fail_playwright)
    monkeypatch.setattr(renderer, "_render_pdf_with_weasyprint", ok_weasy)

    html_path = tmp_path / "in.html"
    html_path.write_text("<html><body>x</body></html>", encoding="utf-8")
    pdf_path = tmp_path / "out.pdf"

    result = renderer.html_file_to_pdf(str(html_path), str(pdf_path))
    assert result.render_engine == "weasyprint"
    assert Path(result.pdf_path).exists()


def test_playwright_missing_browser_binaries_has_actionable_message(monkeypatch, tmp_path: Path):
    renderer = HtmlToPdfRenderer(enable_fallback=False)

    class _Chromium:
        def launch(self, headless=True):
            raise Exception("BrowserType.launch: Executable doesn't exist at /tmp/chrome")

    class _Ctx:
        chromium = _Chromium()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_module = types.SimpleNamespace(sync_playwright=lambda: _Ctx())
    monkeypatch.setattr("career_intent.utils.html_pdf_renderer.importlib.import_module", lambda _name: fake_module)

    html_path = tmp_path / "in.html"
    html_path.write_text("<html><body>x</body></html>", encoding="utf-8")
    pdf_path = tmp_path / "out.pdf"

    with pytest.raises(RuntimeError) as exc:
        renderer.html_file_to_pdf(str(html_path), str(pdf_path))

    message = str(exc.value)
    assert "python -m playwright install chromium" in message
