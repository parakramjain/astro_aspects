from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from reportlab.platypus import PageBreak

from .builders.appendix import build_appendix_story
from .builders.cover import build_cover_story
from .builders.dashboard import build_dashboard_story
from .builders.key_moments import build_key_moments_story
from .builders.milestones import build_milestones_story
from .builders.summary import build_summary_story
from .builders.timeline import build_timeline_story
from .config import ReportConfig
from .i18n import lang_for_text, section_title
from .layout import LayoutContext, build_doc, date_range_label, make_header_footer_drawer, report_title_key, NumberedCanvas
from .normalize import fmt_dt, to_local
from .schema import ReportDataError, ReportJson
from .styles import build_styles, register_fonts

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    invalid = '<>:/\\|?*"'
    return "".join("-" if ch in invalid else ch for ch in name)


def generate_report_pdf(json_data: dict, config: ReportConfig) -> Path:
    """Public API: convert report JSON dict into a single PDF."""

    try:
        data = ReportJson.model_validate(json_data)
    except Exception as exc:
        raise ReportDataError(f"Invalid report JSON: {exc}") from exc

    if config.density == "DETAILED":
        config.include_full_appendix = True
    if config.density == "COMPACT":
        config.include_full_appendix = False

    register_fonts(config)
    styles = build_styles(config)

    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    name = data.input.name
    dob = data.input.dateOfBirth
    start = data.input.reportStartDate
    # locale_timezone should be populated from the input
    config.locale_timezone = data.input.timeZone

    if config.override_file_name:
        file_name = config.override_file_name
    else:
        file_name = config.file_name_template.format(
            name=name,
            dob=dob,
            report_type=config.report_type,
            start=start,
        )

    file_name = _sanitize_filename(file_name)

    out_path = output_dir / file_name

    lang = lang_for_text(config.language_mode)
    ctx = LayoutContext(
        config=config,
        report_title=section_title("report_title", config),
        date_range=date_range_label(data.input.reportStartDate, config.locale_timezone, lang),
    )

    generated_local_iso = fmt_dt(to_local(datetime.now().astimezone(), config.locale_timezone), lang)
    on_page = make_header_footer_drawer(ctx, generated_local_iso)

    doc = build_doc(str(out_path), on_page=on_page)

    story = []
    report_id = f"{name}__{dob}__{config.report_type}__{start}"

    # Section order STRICT
    def _maybe_break(force: bool = False) -> None:
        if force or config.density != "COMPACT":
            story.append(PageBreak())

    story.extend(build_cover_story(data, config, styles))
    _maybe_break(force=True)

    story.extend(build_summary_story(data, config, styles))
    _maybe_break(force=False)

    story.extend(build_dashboard_story(data, config, styles))
    _maybe_break(force=config.density != "COMPACT")

    story.extend(build_timeline_story(data, config, styles, report_id=report_id))
    _maybe_break(force=False)

    story.extend(build_key_moments_story(data, config, styles))
    _maybe_break(force=False)

    story.extend(build_milestones_story(data, config, styles, report_id=report_id))

    if config.include_appendix:
        story.append(PageBreak())
        story.extend(build_appendix_story(data, config, styles, overflow=None))

    doc.build(story, canvasmaker=NumberedCanvas)
    return out_path


def load_config_from_yaml(path: Path) -> ReportConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ReportConfig.model_validate(raw)
