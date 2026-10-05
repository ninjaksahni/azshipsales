from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import streamlit as st

from src.constants import SESSION_UPLOAD_KEYS
from src.parser import parse_shipment_csv
from pathlib import Path

from src.store import ingest_rows, load_store, save_store


@dataclass(frozen=True)
class UploadOutcome:
    message: str
    level: str  # success | warning | error
    stats: dict[str, int]


def _fingerprint(filename: str, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    return f"{filename}:{digest}"


def _upload_keys() -> set[str]:
    raw = st.session_state.get(SESSION_UPLOAD_KEYS)
    if not isinstance(raw, list):
        return set()
    return set(raw)


def _remember_fingerprint(fp: str) -> None:
    keys = list(_upload_keys())
    if fp not in keys:
        keys.append(fp)
    st.session_state[SESSION_UPLOAD_KEYS] = keys


def clear_upload_session_keys() -> None:
    st.session_state.pop(SESSION_UPLOAD_KEYS, None)


def handle_csv_upload(uploaded_file: Any, data_path: Path) -> UploadOutcome | None:
    """
    Parse and ingest one uploaded file once per browser session per content hash.
    Returns None if this exact file was already processed (Streamlit rerun).
    """
    content = uploaded_file.getvalue()
    fp = _fingerprint(uploaded_file.name, content)
    if fp in _upload_keys():
        return None

    store = load_store(data_path)
    try:
        parsed = parse_shipment_csv(content)
        stats = ingest_rows(
            store,
            parsed.rows,
            uploaded_file.name,
            parsed.rows_read,
            parsed.rows_skipped_zero_amount,
        )
    except ValueError as exc:
        return UploadOutcome(str(exc), "error", {})

    save_store(store, data_path)
    _remember_fingerprint(fp)

    imported = stats["rows_imported"]
    backfill = stats.get("coverage_days_backfilled", 0)
    if imported == 0 and backfill == 0:
        level = "warning"
        lead = "No new shipment rows in this file (all duplicates or filtered out)."
    else:
        level = "success"
        lead = f"Imported {imported} new shipment rows."

    msg = (
        f"{lead} "
        f"Skipped {stats['rows_skipped_duplicate']} duplicates · "
        f"Skipped {stats['rows_skipped_zero_amount']} zero-amount/zero-qty"
    )
    timeline_bf = stats.get("timeline_backfilled", 0)
    if backfill:
        msg += f" · Backfilled {backfill} calendar entries"
    if timeline_bf:
        msg += f" · Backfilled {timeline_bf} momentum timelines"

    return UploadOutcome(msg, level, stats)


def format_cached_upload_notice() -> str:
    return "This file was already processed this session."


def handle_csv_uploads(
    uploaded_files: list[Any],
    data_path: Path,
) -> tuple[list[tuple[str, UploadOutcome | None]], bool]:
    """
    Process multiple CSV uploads in order. Returns (per-file results, store_changed).
    """
    results: list[tuple[str, UploadOutcome | None]] = []
    store_changed = False

    for uploaded_file in uploaded_files:
        outcome = handle_csv_upload(uploaded_file, data_path)
        results.append((uploaded_file.name, outcome))
        if outcome is not None and outcome.level in ("success", "warning"):
            store_changed = True

    return results, store_changed
