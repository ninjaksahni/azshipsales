from __future__ import annotations

import streamlit as st

from src.constants import METRIC_UNITS_LABEL, SESSION_METRIC
from src.fulfillment import Metric


def get_metric() -> Metric:
    label = st.session_state.get(SESSION_METRIC, METRIC_UNITS_LABEL)
    return "units" if label == METRIC_UNITS_LABEL else "revenue"
