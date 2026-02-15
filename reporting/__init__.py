"""PDF report generation package (ReportLab Platypus)."""

from .config import ReportConfig
from .renderer import generate_report_pdf

__all__ = ["ReportConfig", "generate_report_pdf"]
