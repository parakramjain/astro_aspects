from __future__ import annotations
import datetime as dt
from typing import List, Optional, Dict, Any
import ast
import pytz
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from schemas import TimelineRequest

def _format_date(val: Any) -> str:
    if isinstance(val, dt.datetime):
        return val.date().isoformat()
    if isinstance(val, dt.date):
        return val.isoformat()
    if isinstance(val, str):
        try:
            return dt.datetime.fromisoformat(val).date().isoformat()
        except ValueError:
            return val[:10] if len(val) >= 10 else val
    return ""

def plot_timeline_gantt(
    payload: TimelineRequest,
    aspect_list: List[List[Any]]
) -> Optional[Any]:
    """Plot a Gantt-style chart using [aspect, nature, start, end, exact]."""
    if not aspect_list:
        print("No data to plot.")
        return None

    def _to_date(val: Any) -> Optional[dt.date]:
        if isinstance(val, dt.datetime):
            return val.date()
        if isinstance(val, dt.date):
            return val
        if isinstance(val, str):
            try:
                return dt.datetime.fromisoformat(val[:10]).date()
            except ValueError:
                return None
        return None

    rows = []
    for aspect, nature, start, end, exact in aspect_list:
        start_dt = _to_date(start)
        end_dt = _to_date(end)
        exact_dt = _to_date(exact)
        if not start_dt or not end_dt:
            continue
        rows.append((str(aspect), str(nature), start_dt, end_dt, exact_dt))

    if not rows:
        print("No valid dates to plot.")
        return None

    fig_height = max(5, 0.5 * len(rows) + 1.5)
    fig_width: float = 16
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    min_date = min(r[2] for r in rows)
    max_date = max(r[3] for r in rows)

    for idx, (aspect, nature, start_dt, end_dt, exact_dt) in enumerate(rows):
        start_num = float(mdates.date2num(start_dt))
        end_num = float(mdates.date2num(end_dt))
        duration = max(end_num - start_num, 0.1)
        color = "green" if nature.lower() == "positive" else "red"

        ax.hlines(y=idx, xmin=start_num, xmax=end_num, colors=color, linewidth=7, zorder=2)
        start_num = mdates.date2num(start_dt)
        ax.scatter([start_num], [idx], color="black", marker="$E$", s=90, zorder=5)
        end_num = mdates.date2num(end_dt)
        ax.scatter([end_num], [idx], color="black", marker="$L$", s=90, zorder=5)
        if exact_dt:
            exact_num = mdates.date2num(exact_dt)
            ax.scatter([exact_num], [idx], color="black", marker=".", s=90, linewidths=1.5, zorder=5)

    timePeriod_text = "1 Year" if payload.timePeriod == '1Y' else "6 Months" if payload.timePeriod == '6M' else "1 Week" if payload.timePeriod == '1W' else "1 Day" if payload.timePeriod == '1D' else payload.timePeriod
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=16)
    ax.set_xlim(float(mdates.date2num(min_date)), float(mdates.date2num(max_date)))
    ax.margins(x=0)
    if timePeriod_text in {"1 Week", "1 Day"}:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=16)
    ax.set_xlabel(str(min_date.year), fontsize=16)
    ax.set_title(f"Period starting {payload.reportStartDate} for {timePeriod_text}", fontsize=18)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.margins(y=0.02)
    fig.subplots_adjust(top=0.92, bottom=0.08)
    return fig

def timeline_report_plot(payload:TimelineRequest, timeline_output: Any) -> None:
    aspect_list: List[List[Any]] = []
    for item in timeline_output.items:
        # print(item.aspect, item.aspectNature, item.startDate, item.exactDate, item.endDate)
        start_date = _format_date(item.startDate)
        end_date = _format_date(item.endDate)
        exact_date = _format_date(item.exactDate)
        aspect_list.append(
            [item.aspect, item.aspectNature, start_date, end_date, exact_date]
        )
    # sort the aspect_list based on start_date, then exact_date in decending order
    aspect_list.sort(key=lambda x: (x[2], x[4], x[0]), reverse=True)

    timeline_plot = plot_timeline_gantt(payload, aspect_list)
    return timeline_plot

