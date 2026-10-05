from __future__ import annotations

import calendar as cal_mod
from datetime import date, datetime
from html import escape
from typing import Any


def ensure_sales_by_day(store: dict[str, Any]) -> dict[str, int]:
    days = store.get("sales_by_day")
    if not isinstance(days, dict):
        days = {}
        store["sales_by_day"] = days
    return days


def record_shipment_day(store: dict[str, Any], shipment_date: str) -> None:
    if not shipment_date:
        return
    days = ensure_sales_by_day(store)
    days[shipment_date] = int(days.get(shipment_date, 0)) + 1


def coverage_summary_text(sales_by_day: dict[str, int]) -> str:
    if not sales_by_day:
        return "No shipment dates recorded yet. Upload a CSV to see which days are covered."

    sorted_days = sorted(sales_by_day.keys())
    start = _parse_day(sorted_days[0])
    end = _parse_day(sorted_days[-1])
    day_count = len(sorted_days)
    month_labels = _month_labels(sorted_days)

    start_s = _format_day(start) if start else sorted_days[0]
    end_s = _format_day(end) if end else sorted_days[-1]

    months_part = ", ".join(month_labels)
    return (
        f"Sales recorded on **{day_count}** day{'s' if day_count != 1 else ''} "
        f"from **{start_s}** through **{end_s}** "
        f"across **{len(month_labels)}** month{'s' if len(month_labels) != 1 else ''}**: {months_part}."
    )


def _format_day(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def _parse_day(day_str: str) -> date | None:
    try:
        return datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _month_labels(sorted_days: list[str]) -> list[str]:
    seen: list[str] = []
    for day_str in sorted_days:
        d = _parse_day(day_str)
        if not d:
            continue
        label = d.strftime("%b %Y")
        if label not in seen:
            seen.append(label)
    return seen


def coverage_calendar_html(sales_by_day: dict[str, int]) -> str:
    if not sales_by_day:
        return ""

    months: list[tuple[int, int]] = []
    for day_str in sorted(sales_by_day.keys()):
        d = _parse_day(day_str)
        if not d:
            continue
        key = (d.year, d.month)
        if key not in months:
            months.append(key)

    blocks: list[str] = []
    max_count = max(sales_by_day.values()) if sales_by_day else 1

    for year, month in months:
        blocks.append(_month_grid_html(year, month, sales_by_day, max_count))

    style = """
    <style>
    .cov-wrap { font-family: sans-serif; font-size: 11px; margin-bottom: 12px; }
    .cov-month { margin-bottom: 10px; }
    .cov-title { font-weight: 600; margin-bottom: 4px; color: #31333F; }
    .cov-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
    .cov-dow { text-align: center; color: #808495; font-size: 9px; padding: 1px 0; }
    .cov-cell { aspect-ratio: 1; border-radius: 2px; min-height: 14px; }
    .cov-empty { background: #f0f2f6; }
    .cov-pad { background: transparent; }
    </style>
    """
    return style + '<div class="cov-wrap">' + "".join(blocks) + "</div>"


def _month_grid_html(
    year: int, month: int, sales_by_day: dict[str, int], max_count: int
) -> str:
    title = date(year, month, 1).strftime("%B %Y")
    weeks = cal_mod.monthcalendar(year, month)
    dow = ["M", "T", "W", "T", "F", "S", "S"]

    header = "".join(f'<div class="cov-dow">{d}</div>' for d in dow)
    cells: list[str] = []

    for week in weeks:
        for day in week:
            if day == 0:
                cells.append('<div class="cov-cell cov-pad"></div>')
                continue
            key = date(year, month, day).isoformat()
            count = sales_by_day.get(key, 0)
            if count:
                intensity = 0.35 + 0.65 * (count / max_count)
                color = f"rgba(255, 75, 75, {intensity:.2f})"
                tip = escape(f"{key}: {count} shipment{'s' if count != 1 else ''}")
                cells.append(
                    f'<div class="cov-cell" style="background:{color}" title="{tip}"></div>'
                )
            else:
                cells.append('<div class="cov-cell cov-empty"></div>')

    return (
        f'<div class="cov-month">'
        f'<div class="cov-title">{escape(title)}</div>'
        f'<div class="cov-grid">{header}{"".join(cells)}</div>'
        f"</div>"
    )
