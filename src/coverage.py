from __future__ import annotations

import calendar as cal_mod
from datetime import date, datetime
from html import escape
from typing import Any

from src.parser import ShipmentRow


def ensure_sales_by_day(store: dict[str, Any]) -> dict[str, int]:
    days = store.get("sales_by_day")
    if not isinstance(days, dict):
        days = {}
        store["sales_by_day"] = days
    return days


def ensure_sales_day_keys(store: dict[str, Any]) -> set[str]:
    keys = store.get("sales_day_keys")
    if not isinstance(keys, list):
        keys = []
        store["sales_day_keys"] = keys
    return set(keys)


def _day_row_key(row: ShipmentRow) -> str:
    return f"{row.dedup_key}|{row.shipment_date}"


def record_shipment_day_for_row(store: dict[str, Any], row: ShipmentRow) -> bool:
    """Record one shipment toward sales_by_day; idempotent per order+SKU+date."""
    if not row.shipment_date:
        return False
    day_keys = ensure_sales_day_keys(store)
    composite = _day_row_key(row)
    if composite in day_keys:
        return False
    days = ensure_sales_by_day(store)
    days[row.shipment_date] = int(days.get(row.shipment_date, 0)) + 1
    day_keys.add(composite)
    store["sales_day_keys"] = sorted(day_keys)
    return True


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
        f"Shipments recorded on **{day_count}** day{'s' if day_count != 1 else ''} "
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


def _heat_color(count: int, max_count: int) -> str:
    """Light block for few shipments → dark block for many."""
    if count <= 0 or max_count <= 0:
        return "#FFFFFF"
    t = min(1.0, count / max_count)
    # Light rose → deep crimson
    light = (255, 229, 229)
    dark = (127, 17, 17)
    r = int(light[0] + (dark[0] - light[0]) * t)
    g = int(light[1] + (dark[1] - light[1]) * t)
    b = int(light[2] + (dark[2] - light[2]) * t)
    return f"rgb({r},{g},{b})"


def _format_tooltip(day: date, count: int, max_count: int) -> str:
    weekday = day.strftime("%A")
    long_date = f"{day.day} {day.strftime('%B %Y')}"
    share = (count / max_count * 100) if max_count > 0 else 0
    lines = [
        f"{weekday}, {long_date}",
        f"{count} shipment{'s' if count != 1 else ''}",
        f"{share:.0f}% of your busiest day",
    ]
    if count == max_count:
        lines.append("Peak day in view")
    return "<br/>".join(escape(line) for line in lines)


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


def shipment_calendar_styles_html() -> str:
    return """
    <style>
    .cov-wrap {
      font-family: sans-serif;
      font-size: 11px;
      margin-bottom: 12px;
      color: var(--text-color, #31333F);
    }
    .cov-month { margin-bottom: 10px; }
    .cov-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
    .cov-dow {
      text-align: center;
      color: var(--text-color, #808495);
      opacity: 0.72;
      font-size: 9px;
      padding: 1px 0;
    }
    .cov-cell {
      aspect-ratio: 1;
      border-radius: 3px;
      min-height: 14px;
      position: relative;
      border: 1px solid rgba(128, 128, 128, 0.15);
    }
    .cov-cell.cov-hot { cursor: help; }
    .cov-empty { background: #FFFFFF !important; }
    .cov-pad { background: transparent; border: none; }
    .cov-tip {
      visibility: hidden;
      opacity: 0;
      position: absolute;
      left: 50%;
      bottom: calc(100% + 6px);
      transform: translateX(-50%);
      background: rgba(20, 20, 24, 0.96);
      color: #fafafa;
      padding: 8px 10px;
      border-radius: 6px;
      font-size: 10px;
      line-height: 1.45;
      text-align: center;
      white-space: nowrap;
      z-index: 9999;
      pointer-events: none;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
    }
    .cov-cell.cov-hot:hover .cov-tip,
    .cov-cell.cov-hot:focus-within .cov-tip {
      visibility: visible;
      opacity: 1;
    }
    </style>
    """


def single_month_calendar_html(
    year: int,
    month: int,
    sales_by_day: dict[str, int],
    max_count: int | None = None,
    *,
    hide_title: bool = False,
) -> str:
    if max_count is None:
        max_count = max(sales_by_day.values()) if sales_by_day else 1
    return _month_grid_html(year, month, sales_by_day, max_count, hide_title=hide_title)


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

    style = (
        shipment_calendar_styles_html()
        + """
    <style>
    .cov-title {
      font-weight: 600;
      margin-bottom: 4px;
      color: #FFFFFF !important;
    }
    .cov-legend {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 9px;
      margin-top: 6px;
      opacity: 0.85;
    }
    .cov-legend-bar {
      flex: 1;
      height: 8px;
      border-radius: 4px;
      background: linear-gradient(90deg, #FFE5E5 0%, #7F1111 100%);
      border: 1px solid rgba(128, 128, 128, 0.2);
    }
    html[data-theme="dark"] .cov-wrap {
      color: rgba(250, 250, 250, 0.95);
    }
    html[data-theme="dark"] .cov-dow {
      color: rgba(250, 250, 250, 0.55);
      opacity: 1;
    }
    </style>
    """
    )
    legend = (
        '<div class="cov-legend">'
        '<span>Fewer</span>'
        '<div class="cov-legend-bar"></div>'
        '<span>More</span>'
        "</div>"
    )
    return style + '<div class="cov-wrap">' + "".join(blocks) + legend + "</div>"


def _month_grid_html(
    year: int,
    month: int,
    sales_by_day: dict[str, int],
    max_count: int,
    *,
    hide_title: bool = False,
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
                day_date = date(year, month, day)
                color = _heat_color(count, max_count)
                tip_html = _format_tooltip(day_date, count, max_count)
                cells.append(
                    f'<div class="cov-cell cov-hot" style="background:{color};" '
                    f'aria-label="{escape(key)}: {count} shipments">'
                    f'<span class="cov-tip">{tip_html}</span></div>'
                )
            else:
                cells.append(
                    '<div class="cov-cell cov-empty" style="background:#FFFFFF;"></div>'
                )

    title_html = (
        ""
        if hide_title
        else f'<div class="cov-title" style="color:#FFFFFF;">{escape(title)}</div>'
    )
    return (
        f'<div class="cov-month">'
        f"{title_html}"
        f'<div class="cov-grid">{header}{"".join(cells)}</div>'
        f"</div>"
    )
