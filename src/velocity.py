from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Literal

WindowDays = 7

MomentumLabel = Literal["surging", "growing", "steady", "cooling", "new", "quiet"]


@dataclass(frozen=True)
class CityMomentum:
    city: str
    label: MomentumLabel
    headline: str
    detail: str
    recent_units: int
    prior_units: int
    change_pct: float | None
    sparkline_days: list[str]
    sparkline_units: list[int]


def _parse_day(day_str: str) -> date | None:
    try:
        return datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def reference_end_date(store: dict[str, Any]) -> date | None:
    days = store.get("sales_by_day", {})
    if not days:
        return None
    parsed = [_parse_day(d) for d in days.keys()]
    valid = [d for d in parsed if d]
    return max(valid) if valid else None


def _sum_window(by_day: dict[str, int], end: date, start_offset: int, length: int) -> int:
    total = 0
    for i in range(length):
        d = end - timedelta(days=start_offset + i)
        total += int(by_day.get(d.isoformat(), 0))
    return total


def classify_momentum(recent: int, prior: int) -> tuple[MomentumLabel, str, str, float | None]:
    if recent == 0 and prior == 0:
        return "quiet", "Quiet", "No shipments in the last two weeks.", None

    if prior == 0 and recent > 0:
        return (
            "new",
            "New demand",
            f"First activity in the last 7 days ({recent} units).",
            None,
        )

    change_pct = ((recent - prior) / prior) * 100.0

    if change_pct >= 50 and recent >= 2:
        return (
            "surging",
            "Surging",
            f"Up {change_pct:.0f}% vs the week before ({recent} vs {prior} units).",
            change_pct,
        )
    if change_pct >= 15:
        return (
            "growing",
            "Picking up",
            f"Up {change_pct:.0f}% vs the week before ({recent} vs {prior} units).",
            change_pct,
        )
    if change_pct <= -25:
        return (
            "cooling",
            "Slowing",
            f"Down {abs(change_pct):.0f}% vs the week before ({recent} vs {prior} units).",
            change_pct,
        )
    return (
        "steady",
        "Steady",
        f"Similar to the prior week ({recent} vs {prior} units).",
        change_pct,
    )


def sparkline_series(by_day: dict[str, int], end: date, days: int = 14) -> tuple[list[str], list[int]]:
    labels: list[str] = []
    values: list[int] = []
    for i in range(days - 1, -1, -1):
        d = end - timedelta(days=i)
        key = d.isoformat()
        labels.append(d.strftime("%d %b"))
        values.append(int(by_day.get(key, 0)))
    return labels, values


def city_momentum(
    city: str,
    by_day: dict[str, int],
    end: date,
) -> CityMomentum | None:
    if not by_day:
        return None

    recent = _sum_window(by_day, end, 0, WindowDays)
    prior = _sum_window(by_day, end, WindowDays, WindowDays)
    label, headline, detail, change_pct = classify_momentum(recent, prior)
    spark_labels, spark_values = sparkline_series(by_day, end)

    return CityMomentum(
        city=city,
        label=label,
        headline=headline,
        detail=detail,
        recent_units=recent,
        prior_units=prior,
        change_pct=change_pct,
        sparkline_days=spark_labels,
        sparkline_units=spark_values,
    )


def momentum_for_sku(
    sku_data: dict[str, Any],
    store: dict[str, Any],
    city_names: list[str],
) -> list[CityMomentum]:
    end = reference_end_date(store)
    if not end:
        return []

    results: list[CityMomentum] = []
    cities = sku_data.get("cities", {})
    for city in city_names:
        bucket = cities.get(city, {})
        by_day = bucket.get("by_day") if isinstance(bucket.get("by_day"), dict) else {}
        item = city_momentum(city, by_day, end)
        if item:
            results.append(item)

    priority = {"surging": 0, "new": 1, "growing": 2, "steady": 3, "cooling": 4, "quiet": 5}
    results.sort(
        key=lambda m: (
            priority.get(m.label, 9),
            -(m.change_pct or 0),
            -m.recent_units,
        )
    )
    return results


def has_timeline_data(sku_data: dict[str, Any]) -> bool:
    for bucket in sku_data.get("cities", {}).values():
        by_day = bucket.get("by_day")
        if isinstance(by_day, dict) and any(int(v) > 0 for v in by_day.values()):
            return True
    return False
