from __future__ import annotations

from typing import Any

import streamlit as st

from src.constants import SESSION_MAP_SKU, SESSION_SKUS
from src.fulfillment import Metric, default_sku, skus_sorted


def _sku_list_and_fallback(skus: dict[str, Any], metric: Metric) -> tuple[list[str], str]:
    sku_list = skus_sorted(skus, metric)
    fallback = default_sku(skus, metric) or sku_list[0]
    return sku_list, fallback


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


def init_sku_selection(skus: dict[str, Any], metric: Metric) -> list[str]:
    """
    Initialize or repair SESSION_SKUS before st.pills(..., key=SESSION_SKUS).
    Safe to call once per run before that widget is created.
    """
    sku_list, fallback = _sku_list_and_fallback(skus, metric)
    selected = _normalize_sku_selection(
        st.session_state.get(SESSION_SKUS),
        sku_list,
        fallback,
    )
    st.session_state[SESSION_SKUS] = selected
    return sku_list


def read_selected_skus(skus: dict[str, Any], metric: Metric) -> list[str]:
    """Read current multi-SKU selection after pills. Does not mutate SESSION_SKUS."""
    sku_list, fallback = _sku_list_and_fallback(skus, metric)
    return _normalize_sku_selection(
        st.session_state.get(SESSION_SKUS),
        sku_list,
        fallback,
    )


def ensure_map_sku(skus: dict[str, Any], metric: Metric) -> str:
    sku_list, _fallback = _sku_list_and_fallback(skus, metric)
    first = read_selected_skus(skus, metric)[0]
    if SESSION_MAP_SKU not in st.session_state or st.session_state[SESSION_MAP_SKU] not in sku_list:
        st.session_state[SESSION_MAP_SKU] = first
    return st.session_state[SESSION_MAP_SKU]


def ensure_default_sku(skus: dict[str, Any], metric: Metric) -> list[str]:
    """Backward-compatible: returns SKU list; initializes selection if needed."""
    return init_sku_selection(skus, metric)
