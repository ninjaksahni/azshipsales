from __future__ import annotations

from typing import Any

import streamlit as st

from src.constants import SESSION_MAP_SKU, SESSION_SKUS
from src.fulfillment import Metric, default_sku, skus_sorted


def _normalize_sku_selection(raw: Any, sku_list: list[str], fallback: str) -> list[str]:
    if isinstance(raw, str):
        raw = [raw] if raw in sku_list else []
    elif isinstance(raw, (list, tuple)):
        raw = [s for s in raw if s in sku_list]
    else:
        raw = []
    if not raw:
        return [fallback]
    return list(dict.fromkeys(raw))


def ensure_default_skus(skus: dict[str, Any], metric: Metric) -> list[str]:
    """Ensure at least one valid SKU is selected; returns sorted SKU list."""
    sku_list = skus_sorted(skus, metric)
    fallback = default_sku(skus, metric) or sku_list[0]
    selected = _normalize_sku_selection(
        st.session_state.get(SESSION_SKUS),
        sku_list,
        fallback,
    )
    st.session_state[SESSION_SKUS] = selected
    return sku_list


def selected_skus(skus: dict[str, Any], metric: Metric) -> list[str]:
    ensure_default_skus(skus, metric)
    return list(st.session_state[SESSION_SKUS])


def ensure_map_sku(skus: dict[str, Any], metric: Metric) -> str:
    sku_list = ensure_default_skus(skus, metric)
    fallback = st.session_state[SESSION_SKUS][0]
    if SESSION_MAP_SKU not in st.session_state or st.session_state[SESSION_MAP_SKU] not in sku_list:
        st.session_state[SESSION_MAP_SKU] = fallback
    return st.session_state[SESSION_MAP_SKU]


# Backward-compatible alias used before multi-select.
def ensure_default_sku(skus: dict[str, Any], metric: Metric) -> list[str]:
    return ensure_default_skus(skus, metric)
