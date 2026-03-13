from __future__ import annotations

import logging
import time
import importlib
import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from career_intent.utils.render_models import RenderResult
except ModuleNotFoundError:  # pragma: no cover - enables direct script execution
    from render_models import RenderResult  # type: ignore


class HtmlToPdfRenderer:
    def __init__(
        self,
        *,
        default_engine: str = "playwright",
        enable_fallback: bool = False,
        timeout_ms: int = 30000,
        default_options: Optional[Dict[str, Any]] = None,
    ):
        self.default_engine = default_engine
        self.enable_fallback = enable_fallback
        self.timeout_ms = timeout_ms
        self.logger = logging.getLogger("career_intent_html_pdf")
        self.default_options: Dict[str, Any] = {
            "format": "A4",
            "print_background": True,
            "margin": {"top": "20px", "right": "20px", "bottom": "20px", "left": "20px"},
        }
        if default_options:
            self.default_options.update(default_options)

    def save_html(self, html_content: str, output_html_path: str) -> str:
        path = Path(output_html_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html_content, encoding="utf-8")
        self.logger.info("Saved HTML to %s", str(path))
        return str(path)

    def _resolve_html_path(self, output_pdf_path: str, output_html_path: str | None) -> str:
        pdf_path = Path(output_pdf_path)
        if output_html_path is None:
            return str(pdf_path.with_suffix(".html"))
        html_path = Path(output_html_path)
        if html_path.suffix.lower() == ".html":
            return str(html_path)
        return str((html_path / pdf_path.with_suffix(".html").name))

    def _merge_options(self, options: Optional[dict]) -> Dict[str, Any]:
        merged = dict(self.default_options)
        if options:
            merged.update(options)
        return merged

    def _count_pages(self, pdf_path: str) -> int | None:
        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            return len(reader.pages)
        except Exception:
            return None

    def _render_pdf_with_playwright(self, input_html_path: str, output_pdf_path: str, options: Dict[str, Any]) -> None:
        try:
            sync_api = importlib.import_module("playwright.sync_api")
            sync_playwright = getattr(sync_api, "sync_playwright")
        except Exception as exc:
            raise RuntimeError(
                "Playwright is not available. Install with:\n"
                "  pip install playwright\n"
                "  python -m playwright install chromium\n"
                f"Original error: {exc}"
            ) from exc

        html_uri = Path(input_html_path).resolve().as_uri()
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:
                message = str(exc)
                if "Executable doesn't exist" in message:
                    raise RuntimeError(
                        "Playwright browser binaries are missing. Run:\n"
                        "  python -m playwright install chromium\n"
                        f"Original error: {exc}"
                    ) from exc
                raise RuntimeError(f"Playwright launch failed: {exc}") from exc
            try:
                page = browser.new_page()
                page.goto(html_uri, wait_until="networkidle", timeout=self.timeout_ms)
                page.pdf(path=output_pdf_path, **options)
            finally:
                browser.close()

    def _render_pdf_with_weasyprint(self, input_html_path: str, output_pdf_path: str) -> None:
        try:
            from weasyprint import HTML  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "WeasyPrint is not available. Install with:\n"
                "  pip install weasyprint\n"
                f"Original error: {exc}"
            ) from exc
        html_text = Path(input_html_path).read_text(encoding="utf-8")
        normalized_html = self._normalize_html_for_weasyprint(html_text)
        HTML(string=normalized_html, base_url=str(Path(input_html_path).resolve().parent)).write_pdf(output_pdf_path)

    def _normalize_html_for_weasyprint(self, html_content: str) -> str:
        normalized = re.sub(r"@media\s*\([^\{]+\)", "@media print", html_content)
        normalized = re.sub(r"@media\s+screen\s+and\s*\([^\{]+\)", "@media print", normalized)
        return normalized

    def readiness(self) -> Dict[str, bool]:
        playwright_ok = False
        weasyprint_ok = False

        try:
            sync_api = importlib.import_module("playwright.sync_api")
            sync_playwright = getattr(sync_api, "sync_playwright")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                browser.close()
            playwright_ok = True
        except Exception:
            playwright_ok = False

        try:
            importlib.import_module("weasyprint")
            weasyprint_ok = True
        except Exception:
            weasyprint_ok = False

        return {
            "playwright_ok": playwright_ok,
            "weasyprint_ok": weasyprint_ok,
        }

    def html_file_to_pdf(self, input_html_path: str, output_pdf_path: str, options: Optional[dict] = None) -> RenderResult:
        start = time.perf_counter()
        html_path = Path(input_html_path)
        pdf_path = Path(output_pdf_path)
        if not html_path.exists():
            raise FileNotFoundError(f"Input HTML not found: {input_html_path}")

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        merged_options = self._merge_options(options)

        engine_used = self.default_engine
        readiness = self.readiness()
        if self.enable_fallback and not readiness.get("playwright_ok", False) and readiness.get("weasyprint_ok", False):
            self.logger.warning("Playwright not ready; using weasyprint fallback directly.")
            self._render_pdf_with_weasyprint(str(html_path), str(pdf_path))
            engine_used = "weasyprint"
        else:
            try:
                self._render_pdf_with_playwright(str(html_path), str(pdf_path), merged_options)
                engine_used = "playwright"
            except Exception as first_exc:
                first_message = str(first_exc)
                if "Playwright browser binaries are missing" in first_message or "Playwright is not available" in first_message:
                    self.logger.warning("Playwright render unavailable for %s -> %s: %s", str(html_path), str(pdf_path), first_message)
                else:
                    self.logger.exception("Playwright render failed for %s -> %s", str(html_path), str(pdf_path))
                if not self.enable_fallback:
                    raise RuntimeError(f"PDF render failed with playwright: {first_exc}") from first_exc
                try:
                    self._render_pdf_with_weasyprint(str(html_path), str(pdf_path))
                except Exception as second_exc:
                    raise RuntimeError(
                        "PDF render failed with both playwright and fallback weasyprint. "
                        f"playwright_error={first_exc}; weasyprint_error={second_exc}"
                    ) from second_exc
                engine_used = "weasyprint"

        if not pdf_path.exists():
            raise RuntimeError(f"PDF generation finished without output file: {output_pdf_path}")

        generation_ms = int((time.perf_counter() - start) * 1000)
        file_size = pdf_path.stat().st_size
        page_count = self._count_pages(str(pdf_path))
        self.logger.info(
            "Rendered PDF engine=%s html=%s pdf=%s size=%s duration_ms=%s",
            engine_used,
            str(html_path),
            str(pdf_path),
            file_size,
            generation_ms,
        )
        return RenderResult(
            success=True,
            html_path=str(html_path),
            pdf_path=str(pdf_path),
            file_size_bytes=file_size,
            page_count=page_count,
            render_engine=engine_used,
            generation_ms=generation_ms,
        )

    def html_to_pdf(
        self,
        html_content: str,
        output_pdf_path: str,
        output_html_path: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> RenderResult:
        html_path = self._resolve_html_path(output_pdf_path, output_html_path)
        saved_html_path = self.save_html(html_content, html_path)
        try:
            return self.html_file_to_pdf(saved_html_path, output_pdf_path, options=options)
        except Exception:
            self.logger.exception("PDF render failed after HTML save. HTML preserved at %s", saved_html_path)
            raise

    def render_html_string_to_temp_pdf(self, html_content: str, output_pdf_path: str, options: Optional[dict] = None) -> RenderResult:
        return self.html_to_pdf(html_content=html_content, output_pdf_path=output_pdf_path, output_html_path=None, options=options)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    renderer = HtmlToPdfRenderer(enable_fallback=True)
    html_path = "output/career_intent_output/parakram_jain_career_progression_report.html"
    pdf_path = "output/career_intent_output/parakram_jain_career_progression_report.pdf"
    try:
        result = renderer.html_file_to_pdf(html_path, pdf_path)
        print(f"PDF generation result: {result}")
    except Exception as exc:
        print("PDF generation failed.")
        print(str(exc))