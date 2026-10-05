from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.velocity import CityMomentum, has_timeline_data, momentum_for_sku

_BADGE = {
    "surging": "🚀 Surging",
    "growing": "📈 Picking up",
    "new": "✨ New demand",
    "steady": "➡️ Steady",
    "cooling": "📉 Slowing",
    "quiet": "· Quiet",
}


def render_market_momentum(
    sku: str,
    sku_data: dict[str, Any],
    store: dict[str, Any],
    priority_cities: list[str],
) -> None:
    st.markdown("##### Market momentum")
    st.caption(
        "Each city is compared on **units shipped**: last **7 days** vs the **7 days before** that."
    )

    if not has_timeline_data(sku_data):
        st.info(
            "Momentum needs daily history per city. **Re-upload your shipment CSV** once "
            "(duplicates are skipped) to backfill timelines — totals stay the same."
        )
        return

    items = momentum_for_sku(sku_data, store, priority_cities)
    if not items:
        st.caption("No timeline data for these markets yet.")
        return

    highlights = [m for m in items if m.label in ("surging", "growing", "new")]
    if highlights:
        st.markdown("**Worth a closer look**")
        for m in highlights[:4]:
            _momentum_row(m)
    else:
        st.success(
            "Top markets look **steady** — no sharp pickup in the last week. "
            "Keep fulfilling to your priority list above."
        )

    with st.expander("All priority markets — momentum detail"):
        for m in items:
            _momentum_row(m)

    spark_target = highlights[0] if highlights else next(
        (m for m in items if m.recent_units > 0), None
    )
    if spark_target and sum(spark_target.sparkline_units) > 0:
        st.markdown(f"**Last 14 days — {spark_target.city}**")
        spark_df = pd.DataFrame(
            {"Units": spark_target.sparkline_units},
            index=spark_target.sparkline_days,
        )
        st.line_chart(spark_df, height=220)


def _momentum_row(m: CityMomentum) -> None:
    badge = _BADGE.get(m.label, m.headline)
    st.markdown(f"{badge} · **{m.city}** — {m.detail}")
