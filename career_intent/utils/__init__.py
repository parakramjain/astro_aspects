from career_intent.utils.file_naming import build_report_file_paths, sanitize_name_for_file
from career_intent.utils.render_models import RenderResult


def __getattr__(name: str):
    if name == "HtmlToPdfRenderer":
        from career_intent.utils.html_pdf_renderer import HtmlToPdfRenderer

        return HtmlToPdfRenderer
    raise AttributeError(name)

__all__ = [
    "HtmlToPdfRenderer",
    "RenderResult",
    "build_report_file_paths",
    "sanitize_name_for_file",
]
