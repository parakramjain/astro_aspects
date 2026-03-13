from __future__ import annotations

from pydantic import BaseModel


class RenderResult(BaseModel):
    success: bool
    html_path: str
    pdf_path: str
    file_size_bytes: int
    page_count: int | None = None
    render_engine: str
    generation_ms: int
