from __future__ import annotations

from typing import Any

import streamlit as st

from src.constants import SESSION_MAP_SKU, SESSION_SKU
from src.fulfillment import Metric, default_sku, skus_sorted


def ensure_default_sku(skus: dict[str, Any], metric: Metric) -> list[str]:
    """Pick first/top SKU when none selected; returns sorted SKU list."""
    sku_list = skus_sorted(skus, metric)
    fallback = default_sku(skus, metric) or sku_list[0]
    if SESSION_SKU not in st.session_state or st.session_state[SESSION_SKU] not in sku_list:
        st.session_state[SESSION_SKU] = fallback
    return sku_list


def ensure_map_sku(skus: dict[str, Any], metric: Metric) -> str:
    sku_list = ensure_default_sku(skus, metric)
    fallback = st.session_state[SESSION_SKU]
    if SESSION_MAP_SKU not in st.session_state or st.session_state[SESSION_MAP_SKU] not in sku_list:
        st.session_state[SESSION_MAP_SKU] = fallback
    return st.session_state[SESSION_MAP_SKU]
